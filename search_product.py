from database.db import SessionLocal
from services.product_service import search_products

session = SessionLocal()

search_term = input("Wpisz kod, EAN lub fragment nazwy produktu: ")

results = search_products(session, search_term)

if not results:
    print("Nie znaleziono żadnego produktu.")
elif len(results) == 1:
    product = results[0]
    print(f"Znaleziono: {product.name} (kod produktu: {product.code}, EAN: {product.ean}, ilość: {product.quantity})")
else:
    print(f"Znaleziono {len(results)} pasujących produktów:")
    for product in results:
        print(f"- {product.name} (kod produktu: {product.code}, EAN: {product.ean}, ilość: {product.quantity})")

session.close()