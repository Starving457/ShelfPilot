from database.db import SessionLocal
from database.models import Product

session = SessionLocal()

code = input("Podaj kod produktu: ")
ean = input("Podaj EAN: ")
name = input("Podaj nazwę produktu: ")
quantity = int(input("Podaj ilość: "))

new_product = Product(code=code, ean=ean, name=name, quantity=quantity)

session.add(new_product)
session.commit()

print(f"Dodano produkt: {name} (kod produktu: {code}, EAN: {ean}, ilość: {quantity})")

session.close()