from database.db import SessionLocal
from database.models import Product
from services.location_service import (
    find_product,
    create_location,
    add_product_to_location,
)

# Dane testowe: kod, EAN, nazwa, stan WAPRO, lokalizacje
LOKALIZACJE = ["A1", "A2", "A3"]

PRODUKTY = [
    ("T001", "1000000000011", "VORTEX DIAMONDBACK HD 10X42 LORNETKA", 4, ["A1"]),
    ("T002", "1000000000028", "VORTEX CROSSFIRE II 3-9X40 LUNETA", 3, ["A1", "A2"]),
    ("T003", "1000000000035", "SWAROVSKI EL RANGE 10X42 LORNETKA", 2, ["A2"]),
    ("T004", "1000000000042", "SWAROVSKI Z8I 2,3-18X56 LUNETA CELOWNICZA", 1, ["A3"]),
    ("T005", "1000000000059", "ZEISS CONQUEST HDX 8X42 LORNETKA", 5, ["A3"]),
    ("T006", "1000000000066", "HOLOSUN HE510C KOLIMATOR", 6, []),
]

session = SessionLocal()

for code in LOKALIZACJE:
    create_location(session, code)

for code, ean, name, quantity, locations in PRODUKTY:
    if find_product(session, code) is not None:
        continue

    product = Product(code=code, ean=ean, name=name, wapro_quantity=quantity)
    session.add(product)
    session.commit()

    for location_code in locations:
        add_product_to_location(session, product, location_code)

print(f"Gotowe: {len(LOKALIZACJE)} lokalizacje i {len(PRODUKTY)} produktów testowych.")

session.close()