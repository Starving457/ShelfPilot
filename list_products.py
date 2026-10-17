from database.db import SessionLocal
from database.models import Product
from services.location_service import get_product_locations

session = SessionLocal()

products = session.query(Product).all()

if not products:
    print("Baza produktów jest pusta.")
else:
    for product in products:
        locations = get_product_locations(session, product)
        if locations:
            kody = ", ".join(loc.code for loc in locations)
        else:
            kody = "brak lokalizacji"
        print(f"{product.code} | {product.name} | stan WAPRO: {product.wapro_quantity} | {kody}")

session.close()