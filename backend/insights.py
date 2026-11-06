"""Pure data-processing helpers for the Nutritional Insights API."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

import numpy as np
import pandas as pd


MACROS = ["Protein(g)", "Carbs(g)", "Fat(g)"]
REQUIRED_COLUMNS = ["Diet_type", "Recipe_name", "Cuisine_type", *MACROS]


def clean_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the columns used by the dashboard."""
    data = dataframe.copy()
    data.columns = data.columns.str.strip()

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    for column in ["Diet_type", "Recipe_name", "Cuisine_type"]:
        data[column] = data[column].astype("string").str.strip()

    data["Diet_type"] = data["Diet_type"].str.lower().fillna("unknown")
    data["Cuisine_type"] = data["Cuisine_type"].str.lower().fillna("unknown")
    data["Recipe_name"] = data["Recipe_name"].fillna("Unnamed recipe")

    for column in MACROS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        mean_value = data[column].mean()
        if pd.isna(mean_value):
            raise ValueError(f"Column {column} has no usable numeric values")
        data[column] = data[column].fillna(mean_value)

    return data


def build_dashboard_payload(
    dataframe: pd.DataFrame,
    *,
    diet_filter: str | None = None,
    source: str = "Azure Blob Storage",
    started_at: float | None = None,
) -> dict[str, object]:
    """Return every chart series and metadata needed by the dashboard."""
    timer_start = started_at if started_at is not None else perf_counter()
    data = clean_data(dataframe)
    available_diets = sorted(data["Diet_type"].dropna().unique().tolist())

    selected_diet = (diet_filter or "all").strip().lower()
    if selected_diet not in {"", "all"}:
        if selected_diet not in available_diets:
            raise ValueError(f"Unknown diet type: {selected_diet}")
        data = data[data["Diet_type"] == selected_diet].copy()
    else:
        selected_diet = "all"

    averages = (
        data.groupby("Diet_type", as_index=False)[MACROS]
        .mean()
        .sort_values("Diet_type")
        .round(2)
        .rename(
            columns={
                "Diet_type": "diet",
                "Protein(g)": "protein",
                "Carbs(g)": "carbs",
                "Fat(g)": "fat",
            }
        )
    )

    distribution = (
        data["Diet_type"]
        .value_counts()
        .rename_axis("diet")
        .reset_index(name="recipes")
        .sort_values("diet")
    )

    scatter_source = data.nlargest(min(140, len(data)), "Protein(g)")
    scatter_points = [
        {
            "diet": row["Diet_type"],
            "recipe": row["Recipe_name"],
            "cuisine": row["Cuisine_type"],
            "protein": round(float(row["Protein(g)"]), 2),
            "carbs": round(float(row["Carbs(g)"]), 2),
            "fat": round(float(row["Fat(g)"]), 2),
        }
        for _, row in scatter_source.iterrows()
    ]

    correlation = data[MACROS].corr().round(3).replace({np.nan: None})
    correlation_matrix = {
        "labels": ["Protein", "Carbs", "Fat"],
        "values": correlation.values.tolist(),
    }

    top_recipes_frame = data.nlargest(min(10, len(data)), "Protein(g)")
    top_recipes = [
        {
            "recipe": row["Recipe_name"],
            "diet": row["Diet_type"],
            "cuisine": row["Cuisine_type"],
            "protein": round(float(row["Protein(g)"]), 2),
        }
        for _, row in top_recipes_frame.iterrows()
    ]

    execution_ms = round((perf_counter() - timer_start) * 1000, 2)
    return {
        "summary": {
            "recipeCount": int(len(data)),
            "dietTypeCount": int(data["Diet_type"].nunique()),
            "averageProtein": round(float(data["Protein(g)"].mean()), 2),
        },
        "availableDiets": available_diets,
        "selectedDiet": selected_diet,
        "averageMacronutrients": averages.to_dict(orient="records"),
        "recipeDistribution": distribution.to_dict(orient="records"),
        "scatterPoints": scatter_points,
        "correlationMatrix": correlation_matrix,
        "topRecipes": top_recipes,
        "metadata": {
            "functionExecutionMs": execution_ms,
            "processedAtUtc": datetime.now(timezone.utc).isoformat(),
            "source": source,
        },
    }
