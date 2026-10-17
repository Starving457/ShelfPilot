from database.db import SessionLocal
from services.product_service import search_products
from services.location_service import get_product_locations

session = SessionLocal()

while True:
    term = input("\nSzukaj po kodzie, EAN lub nazwie (Enter, by zakończyć): ")
    if term == "":
        break

    results = search_products(session, term)

    if not results:
        print("Nic nie znaleziono.")
        continue

    for product in results:
        locations = get_product_locations(session, product)
        if locations:
            kody = ", ".join(loc.code for loc in locations)
        else:
            kody = "brak lokalizacji"
        print(f"{product.code} | {product.name} | {kody}")

session.close()