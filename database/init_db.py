from database.db import engine, Base
from database.models import Product, Location


print("Creating database...")


Base.metadata.create_all(engine)


print("Database created!")