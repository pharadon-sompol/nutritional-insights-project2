"""Azure Functions HTTP API for the Nutritional Insights dashboard."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from time import perf_counter

import azure.functions as func
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from insights import build_dashboard_payload


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _load_dataframe() -> tuple[pd.DataFrame, str]:
    """Load the dataset from Blob Storage, with a local-only fallback."""
    connection_string = os.getenv("NUTRITION_STORAGE_CONNECTION_STRING")
    storage_account_url = os.getenv("STORAGE_ACCOUNT_URL")
    container_name = os.getenv("DATA_CONTAINER_NAME", "datasets")
    blob_name = os.getenv("DATA_BLOB_NAME", "All_Diets.csv")

    if storage_account_url:
        service = BlobServiceClient(
            account_url=storage_account_url,
            credential=DefaultAzureCredential(),
        )
        blob = service.get_blob_client(container=container_name, blob=blob_name)
        content = blob.download_blob().readall()
        return pd.read_csv(io.BytesIO(content)), "Azure Blob Storage"

    if connection_string:
        service = BlobServiceClient.from_connection_string(connection_string)
        blob = service.get_blob_client(container=container_name, blob=blob_name)
        content = blob.download_blob().readall()
        return pd.read_csv(io.BytesIO(content)), "Azure Blob Storage"

    local_path = Path(os.getenv("DATASET_PATH", "All_Diets.csv"))
    if local_path.exists():
        return pd.read_csv(local_path), "Local development file"

    raise RuntimeError(
        "Dataset is not configured. Set STORAGE_ACCOUNT_URL, "
        "NUTRITION_STORAGE_CONNECTION_STRING, or DATASET_PATH."
    )


def _response(body: dict[str, object], status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": os.getenv("ALLOWED_ORIGIN", "*"),
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Cache-Control": "no-store",
        },
    )


@app.route(route="insights", methods=["GET", "OPTIONS"])
def insights(req: func.HttpRequest) -> func.HttpResponse:
    """Return processed chart data and cloud execution metadata."""
    if req.method == "OPTIONS":
        return _response({}, 204)

    started_at = perf_counter()
    try:
        dataframe, source = _load_dataframe()
        payload = build_dashboard_payload(
            dataframe,
            diet_filter=req.params.get("diet"),
            source=source,
            started_at=started_at,
        )
        return _response(payload)
    except ValueError as error:
        return _response({"error": str(error)}, 400)
    except Exception as error:  # Azure logs keep the detailed exception.
        return _response(
            {"error": "The nutritional dataset could not be processed.", "detail": str(error)},
            500,
        )
