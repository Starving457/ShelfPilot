from database.db import SessionLocal
from services.location_service import find_products_by_location

session = SessionLocal()

while True:
    location_code = input("Podaj kod lokalizacji (Enter, by zakończyć): ")

    if location_code == "":
        print("Do zobaczenia!")
        break

    products = find_products_by_location(session, location_code)

    if not products:
        print(f"Brak produktów na lokalizacji {location_code} (albo taka lokalizacja nie istnieje).")
    else:
        print(f"Produkty na lokalizacji {location_code}:")
        for product in products:
            print(f"- {product.name} (kod: {product.code}, ilość: {product.quantity})")

session.close()