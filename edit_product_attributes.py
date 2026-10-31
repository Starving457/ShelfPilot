from database.db import SessionLocal
from services.location_service import find_product
from services.classification_service import (
    set_product_attributes,
    list_manufacturers,
    list_categories,
)

session = SessionLocal()

while True:
    code = input("\nPodaj kod produktu do poprawienia (Enter, by zakończyć): ")
    if code == "":
        break

    product = find_product(session, code)
    if product is None:
        print("Nie znaleziono produktu o takim kodzie.")
        continue

    print(f"Znaleziono: {product.name}")
    print(f"Obecnie: {product.manufacturer or '-'} / {product.category or '-'}")

    manufacturers = list_manufacturers(session)
    categories = list_categories(session)
    if manufacturers:
        print(f"Używani producenci: {', '.join(manufacturers)}")
    if categories:
        print(f"Używane kategorie: {', '.join(categories)}")

    manufacturer = input("Nowy producent (Enter, by anulować): ").strip()
    if manufacturer == "":
        print("Anulowano.")
        continue
    category = input("Nowa kategoria (Enter, by anulować): ").strip()
    if category == "":
        print("Anulowano.")
        continue

    if set_product_attributes(session, product, manufacturer, category) == "ok":
        print(f"Zapisano: {manufacturer} / {category}")

session.close()