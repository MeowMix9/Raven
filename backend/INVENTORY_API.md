# Raven Inventory JSON API (MVP)

This API serves the latest validated Forward Merch inventory snapshot as JSON. n8n remains the ingestion/automation layer; clients only receive the read-only endpoints and data permitted by their API key.

## Endpoints

### Import a snapshot (automation only)

`POST /api/v1/inventory/import`

Header: `X-Raven-Ingest-Key: <RAVEN_INVENTORY_INGEST_KEY>`

Body:

```json
{
  "source": "forward_merch",
  "items": [
    {
      "sku": "ACD1037BLKMD",
      "show": "",
      "item": "ACD1037 : ACD1037BLKMD",
      "description": "BLK ANGUS OVAL SS T-SHIRT",
      "quantity_available": 6,
      "unit_price": 12.5,
      "map_price": 12.5,
      "product_title": "AC/DC Angus Oval T-Shirt",
      "variant_title": "Medium",
      "image_url": "https://supplier-image.example/image.jpg"
    }
  ]
}
```

The API validates records and duplicate SKUs, then saves the whole import as a new snapshot. The previous snapshot remains available internally for audit/recovery; reads use the newest snapshot.

### List inventory (client)

`GET /api/v1/inventory?page=1&page_size=100`

Optional query parameters:
- `q`: case-insensitive search in SKU, description, and product title.
- `sku_prefix`: filter by SKU prefix.
- `available_only=true`: omit zero-stock and unknown-stock records.
- `page` and `page_size`: page starts at 1; page size is capped at 500.

Header: `Authorization: Bearer <CLIENT_API_KEY>`

Returns `data`, `pagination`, and `snapshot` metadata.

### Retrieve one SKU (client)

`GET /api/v1/inventory/{sku}`

Uses the same bearer key. Items hidden by that client's quantity policy return 404, avoiding disclosure that a hidden SKU exists.

## Client keys and visibility policy

From the `backend/` directory, with the database configured and migrations applied:

```bash
python scripts/create_inventory_api_key.py --client-code example-client --name "Example Client"
```

The raw API key is printed once. Store it securely and provide it to the client over a secure channel. Raven stores only a SHA-256 hash.

To hide products with fewer than 3 available units for one client:

```bash
python scripts/create_inventory_api_key.py --client-code example-client --name "Example Client" --minimum-quantity-available 3
```

A missing threshold means no client-specific quantity filter. The shared imported snapshot is not modified by client visibility policies.

## Local setup

1. Set `RAVEN_DATABASE_URL` and a strong, random `RAVEN_INVENTORY_INGEST_KEY` in the environment.
2. Start PostgreSQL using the existing Compose configuration.
3. From `backend/`, install the project and apply migrations:

   ```bash
   pip install -e ".[dev]"
   alembic upgrade head
   ```

4. Start the API:

   ```bash
   uvicorn raven.main:app --host 127.0.0.1 --port 8000
   ```

5. Create a client key with the command above. The API documentation is available at `/docs` while the service is running.

Do not expose the PostgreSQL port publicly. Put the API behind HTTPS before sending a client API key or production inventory data over the internet.