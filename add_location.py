from database.db import SessionLocal
from services.location_service import find_location, create_location

session = SessionLocal()

while True:
    # Regał: tylko litery. Enter kończy cały skrypt.
    rack = input("\nPodaj regał, np. A (Enter, by zakończyć): ").strip().upper()
    if rack == "":
        break
    if not rack.isalpha():
        print("Regał może zawierać tylko litery.")
        continue

    # Półka: tylko cyfry. Pytamy do skutku, Enter anuluje.
    while True:
        shelf = input("Podaj numer półki, np. 1 (Enter, by anulować): ").strip()
        if shelf == "" or shelf.isdigit():
            break
        print("Numer półki może zawierać tylko cyfry.")

    if shelf == "":
        print("Anulowano.")
        continue

    code = rack + shelf

    if find_location(session, code) is not None:
        print(f"Lokalizacja {code} już istnieje.")
        continue

    # Potwierdzenie: Tak / Nie / Edytuj
    while True:
        answer = input(f"Zapisać lokalizację {code}? [T]ak / [N]ie / [E]dytuj: ").strip().upper()
        if answer in ("T", "N", "E"):
            break
        print("Wybierz T, N lub E.")

    if answer == "E":
        print("Wprowadź dane ponownie.")
        continue

    if answer == "N":
        print("Anulowano.")
        continue

    status = create_location(session, rack, shelf)
    if status == "ok":
        print(f"Dodano lokalizację {code}.")
    else:
        print(f"Lokalizacja {code} już istnieje.")

session.close()