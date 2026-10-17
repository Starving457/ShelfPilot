from database.db import SessionLocal
from services.location_service import (
    find_product,
    get_product_locations,
    add_product_to_location,
    remove_product_from_location,
    move_product_location,
)

# Komunikaty dla statusów zwracanych przez services
KOMUNIKATY = {
    "ok": "Gotowe.",
    "location_not_found": "Nie ma takiej lokalizacji.",
    "already_assigned": "Produkt jest już na tej lokalizacji.",
    "not_assigned": "Produkt nie jest przypisany do tej lokalizacji.",
}


def pokaz_lokalizacje(session, product):
    """Wypisuje wszystkie półki, na których leży produkt."""
    locations = get_product_locations(session, product)
    if not locations:
        print("Ten produkt nie ma jeszcze żadnej lokalizacji.")
    else:
        kody = ", ".join(loc.code for loc in locations)
        print(f"Obecne lokalizacje: {kody}")


session = SessionLocal()

while True:
    code = input("\nPodaj kod produktu (Enter, by zakończyć): ")
    if code == "":
        break

    product = find_product(session, code)
    if product is None:
        print("Nie znaleziono produktu o takim kodzie.")
        continue

    print(f"Znaleziono: {product.name}")
    pokaz_lokalizacje(session, product)

    action = input("Co chcesz zrobić? [D]odaj / [P]rzenieś / [U]suń / Enter = nic: ").upper()

    if action == "":
        print("Nic nie zmieniono.")

    elif action == "D":
        new_code = input("Kod lokalizacji do dodania (Enter, by anulować): ")
        if new_code != "":
            status = add_product_to_location(session, product, new_code)
            print(KOMUNIKATY[status])

    elif action == "P":
        from_code = input("Z której lokalizacji przenieść (Enter, by anulować): ")
        if from_code != "":
            to_code = input("Na którą lokalizację (Enter, by anulować): ")
            if to_code != "":
                status = move_product_location(session, product, from_code, to_code)
                print(KOMUNIKATY[status])

    elif action == "U":
        del_code = input("Z której lokalizacji usunąć (Enter, by anulować): ")
        if del_code != "":
            status = remove_product_from_location(session, product, del_code)
            print(KOMUNIKATY[status])

    else:
        print("Nieznana opcja - wybierz D, P lub U.")

    pokaz_lokalizacje(session, product)

session.close()