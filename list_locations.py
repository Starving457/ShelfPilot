from database.db import SessionLocal
from database.models import Location

session = SessionLocal()
locations = session.query(Location).all()
for location in locations:
    print(f"{location.code} | {location.rack} | {location.shelf}")
session.close()