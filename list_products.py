from database.db import SessionLocal
from database.models import Product

session = SessionLocal()
products = session.query(Product).all()

for product in products:
    print(f"{product.id} | {product.code} | {product.name} | {product.quantity} szt.")


session.close()