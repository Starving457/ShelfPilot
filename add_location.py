from database.db import SessionLocal
from services.location_service import find_location, create_location

session = SessionLocal()

while True:
    # Kod regału: litery i cyfry, zaczyna się od litery (np. A1). Enter kończy skrypt.
    code = input("\nPodaj kod regału, np. A1 (Enter, by zakończyć): ").strip().upper()
    if code == "":
        break
    if not (code.isalnum() and code[0].isalpha()):
        print("Kod musi zaczynać się od litery i zawierać tylko litery i cyfry, np. A1.")
        continue

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
        print("Wprowadź kod ponownie.")
        continue

    if answer == "N":
        print("Anulowano.")
        continue

    status = create_location(session, code)
    if status == "ok":
        print(f"Dodano lokalizację {code}.")
    else:
        print(f"Lokalizacja {code} już istnieje.")

session.close()