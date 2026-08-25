from database.db import SessionLocal
from database.models import Product, Location

session = SessionLocal()

code_to_find = "ABC123"

product = session.query(Product).filter(Product.code == code_to_find).first()

if product is None:
    print("Nie znaleziono produktu o takim kodzie.")
else:
    print(f"Znaleziono: {product.name}")

if product.location_id is None:
        print("Ten produkt nie ma jeszcze przypisanej lokalizacji.")

        location_code = "A1"  # na razie na sztywno

        location = session.query(Location).filter(Location.code == location_code).first()

        if location is None:
            print(f"Nie ma takiej lokalizacji: {location_code}")
        else:
            product.location_id = location.id
            session.commit()
            print(f"Przypisano lokalizację {location.code} do produktu {product.name}")
else:
        current_location = session.query(Location).filter(Location.id == product.location_id).first()
        print(f"Obecna lokalizacja: {current_location.code}")

session.close()