from database.db import SessionLocal
from services.location_service import find_location, find_products_by_location

session = SessionLocal()

while True:
    code = input("\nPodaj kod lokalizacji (Enter, by zakończyć): ")
    if code == "":
        break

    if find_location(session, code) is None:
        print("Nie ma takiej lokalizacji.")
        continue

    products = find_products_by_location(session, code)

    if not products:
        print(f"Na lokalizacji {code} nic nie ma.")
        continue

    print(f"Na lokalizacji {code}:")
    for product in products:
        print(f"  {product.code} | {product.name}")

session.close()