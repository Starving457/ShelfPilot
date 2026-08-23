from database.db import SessionLocal
from database.models import Location

session = SessionLocal()


locations = [
    Location(code="A1", rack="A", shelf="1"),
    Location(code="A2", rack="A", shelf="2"),
    Location(code="B1", rack="B", shelf="1"),
]

session.add_all(locations)
session.commit()
session.close()