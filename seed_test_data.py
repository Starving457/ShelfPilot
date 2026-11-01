from datetime import date

from database.db import SessionLocal
from database.models import Product
from services.location_service import (
    find_product,
    create_location,
    add_product_to_location,
)
from services.classification_service import set_product_attributes
from services.inventory_service import record_count

LOCATIONS = ["A1", "A2", "A3"]

# code, EAN, name, WAPRO stock, locations, (manufacturer, category) or None, (count date, counted quantity) or None
PRODUCTS = [
    ("T001", "1000000000011", "VORTEX DIAMONDBACK HD 10X42 LORNETKA", 4, ["A1"], ("Vortex", "Lornetka"), (date(2026, 10, 20), 4)),
    ("T002", "1000000000028", "VORTEX CROSSFIRE II 3-9X40 LUNETA", 3, ["A1", "A2"], ("Vortex", "Luneta"), (date(2026, 10, 20), 2)),
    ("T003", "1000000000035", "SWAROVSKI EL RANGE 10X42 LORNETKA", 2, ["A2"], ("Swarovski", "Lornetka"), None),
    ("T004", "1000000000042", "SWAROVSKI Z8I 2,3-18X56 LUNETA CELOWNICZA", 1, ["A3"], ("Swarovski", "Luneta"), None),
    ("T005", "1000000000059", "ZEISS CONQUEST HDX 8X42 LORNETKA", 5, ["A3"], ("Zeiss", "Lornetka"), (date(2026, 10, 27), 5)),
    ("T006", "1000000000066", "HOLOSUN HE510C KOLIMATOR", 6, [], None, None),
    ("T007", "1000000000073", "VORTEX VIPER HD 10X42 LORNETKA", 0, [], ("Vortex", "Lornetka"), None),
    ("T008", "1000000000080", "VORTEX CROSSFIRE HD 10X42 LORNETKA", 2, ["A1"], ("Vortex", "Lornetka"), None),
]

session = SessionLocal()

for code in LOCATIONS:
    create_location(session, code)

created = 0
for code, ean, name, quantity, locations, attributes, count in PRODUCTS:
    if find_product(session, code) is not None:
        continue

    product = Product(code=code, ean=ean, name=name, wapro_quantity=quantity)
    session.add(product)
    session.commit()
    created += 1

    for location_code in locations:
        add_product_to_location(session, product, location_code)

    if attributes is not None:
        set_product_attributes(session, product, attributes[0], attributes[1])

    if count is not None:
        record_count(session, product, count[1], counted_at=count[0])

print(f"Done: {len(LOCATIONS)} locations, {created} new test products ({len(PRODUCTS)} in the set).")

session.close()