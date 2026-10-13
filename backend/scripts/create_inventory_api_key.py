"""Create a client API key and print the raw key once.

Run from backend/: python scripts/create_inventory_api_key.py --client-code example --name "Example Client"
Use --minimum-quantity-available 3 to hide inventory below three units for that client.
"""
import argparse
import secrets

from sqlalchemy import select

from raven.api.inventory import hash_api_key
from raven.database.session import get_session_factory
from raven.infrastructure.models.inventory import InventoryApiClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-code", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--minimum-quantity-available", type=int, default=None)
    args = parser.parse_args()

    if args.minimum_quantity_available is not None and args.minimum_quantity_available < 0:
        parser.error("--minimum-quantity-available cannot be negative")

    raw_key = "raven_live_" + secrets.token_urlsafe(32)
    factory = get_session_factory()
    with factory() as db:
        existing = db.scalar(
            select(InventoryApiClient).where(
                InventoryApiClient.client_code == args.client_code
            )
        )
        if existing:
            parser.error("That client code already exists; use a new code or rotate the key deliberately.")

        client = InventoryApiClient(
            client_code=args.client_code,
            name=args.name,
            api_key_hash=hash_api_key(raw_key),
            minimum_quantity_available=args.minimum_quantity_available,
            is_active=True,
        )
        db.add(client)
        db.commit()

    print("API key created. Copy it now; Raven stores only its hash.")
    print(raw_key)


if __name__ == "__main__":
    main()
