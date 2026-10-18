from database.db import SessionLocal
from database.models import Product
from services.location_service import find_product

session = SessionLocal()

print("Dodawanie produktu (Enter przy kodzie anuluje).")

code = input("Podaj kod produktu: ")

if code == "":
    print("Anulowano.")
elif find_product(session, code) is not None:
    print("Produkt o takim kodzie już istnieje.")
else:
    ean = input("Podaj EAN (Enter, jeśli brak): ")

    # Nazwa jest wymagana - pytamy do skutku
    while True:
        name = input("Podaj nazwę produktu: ")
        if name != "":
            break
        print("Nazwa nie może być pusta.")

    # Ilość musi być liczbą całkowitą - pytamy do skutku
    while True:
        quantity_text = input("Podaj ilość: ")
        if quantity_text.isdigit():
            quantity = int(quantity_text)
            break
        print("Ilość musi być liczbą całkowitą (0 lub więcej).")

    new_product = Product(code=code, ean=ean, name=name, wapro_quantity=quantity)
    session.add(new_product)
    session.commit()

    print(f"Dodano produkt: {name} (kod produktu: {code}, EAN: {ean}, ilość: {quantity})")

session.close()