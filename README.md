# Nutritional Insights — Project 2

This project moves the Phase 1 nutritional analysis into Azure and exposes the results through a responsive dashboard.

## Architecture

1. `All_Diets.csv` is stored in a private Azure Blob Storage container named `datasets`.
2. An HTTP-triggered Azure Function downloads and processes the CSV with pandas.
3. The Function returns chart-ready JSON plus execution metadata.
4. The static frontend fetches that JSON and renders three required visualizations plus a correlation heatmap.

## Project structure

- `backend/` — Python Azure Function and data-processing tests.
- `frontend/` — buildless HTML/CSS/JavaScript dashboard.
- `docs/evidence/` — reserved for submission screenshots (not committed).

## Run locally

For the quickest local preview, use the bundled validation server from the project root:

```bash
python dev_server.py
```

It serves both the frontend and a local version of the API at `http://localhost:8000`.

To run the real Azure Functions host locally instead:

1. Copy `backend/local.settings.example.json` to `backend/local.settings.json`.
2. Create a Python 3.12 virtual environment and install `backend/requirements.txt`.
3. From `backend/`, run `func start`.
4. From `frontend/`, run `python3 -m http.server 8000`.
5. Open `http://localhost:8000`.

The checked-in `frontend/config.js` points to the deployed Azure Function endpoint. For local-only development, it can be changed temporarily to `/api/insights`.

```js
window.APP_CONFIG = {
  API_URL: "https://YOUR-FUNCTION.azurewebsites.net/api/insights"
};
```

## Required Azure application settings

- `STORAGE_ACCOUNT_URL` — Blob service URL, for example `https://ACCOUNT.blob.core.windows.net`.
- `DATA_CONTAINER_NAME` — `datasets`.
- `DATA_BLOB_NAME` — `All_Diets.csv`.
- `ALLOWED_ORIGIN` — the final Static Web App URL.

The deployed Function uses its managed identity with the **Storage Blob Data Reader** role, so no Storage Account key is stored in the code or application settings. A connection-string fallback remains available for local development only.

## Test the data processing

From `backend/`:

```bash
python -m unittest discover -s tests -v
```

## Deployed resources

- Azure Function endpoint: `https://func-nutri-p2-ps1105.azurewebsites.net/api/insights`
- Static dashboard URL: `https://proud-stone-00f69ae10.8.azurestaticapps.net`
- GitHub repository: `https://github.com/pharadon-sompol/nutritional-insights-project2`

The Azure resources are grouped in `rg-nutritional-insights-p2`. The private dataset is stored in the `datasets` container of storage account `stnutrip2ps1105`. The Function App is `func-nutri-p2-ps1105`, and the Static Web App is `swa-nutri-p2-ps1105` on the Free plan.
