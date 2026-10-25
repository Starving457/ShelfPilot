from database.db import SessionLocal
from services.location_service import list_locations, find_products_by_location

session = SessionLocal()

locations = list_locations(session)

if not locations:
    print("Brak lokalizacji. Dodaj je przez add_location.py.")
else:
    print("Lokalizacje:")
    for location in locations:
        count = len(find_products_by_location(session, location.code))
        print(f"  {location.code} - produktów: {count}")

session.close()