from database.db import SessionLocal
from services.location_service import (
    find_location,
    find_products_by_location,
    delete_location,
)

session = SessionLocal()

while True:
    code = input("\nPodaj kod lokalizacji do usunięcia (Enter, by zakończyć): ").strip().upper()
    if code == "":
        break

    if find_location(session, code) is None:
        print("Nie ma takiej lokalizacji.")
        continue

    products = find_products_by_location(session, code)
    if products:
        print(f"Nie można usunąć {code}: leży na niej produktów: {len(products)}.")
        print("Najpierw przenieś je na inną półkę (assign_location.py).")
        continue

    while True:
        answer = input(f"Na pewno usunąć lokalizację {code}? [T]ak / [N]ie: ").strip().upper()
        if answer in ("T", "N"):
            break
        print("Wybierz T lub N.")

    if answer == "N":
        print("Anulowano.")
        continue

    status = delete_location(session, code)
    if status == "ok":
        print(f"Usunięto lokalizację {code}.")
    else:
        print("Nie udało się usunąć lokalizacji.")

session.close()