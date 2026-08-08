from database.db import SessionLocal
from database.models import Product

session = SessionLocal()

new_product = Product(code="ABC123", name="Śruba", quantity=10)

session.add(new_product)
session.commit()
session.close()