from database.db import SessionLocal
from services.location_service import (
    find_product,
    find_location_by_id,
    assign_new_location,
    update_location,
    remove_location,
)

session = SessionLocal()

while True:
    code_to_find = input("Podaj kod produktu (Enter, by zakończyć): ")

    if code_to_find == "":
        print("Do zobaczenia!")
        break

    product = find_product(session, code_to_find)

    if product is None:
        print("Nie znaleziono produktu o takim kodzie.")
    else:
        print(f"Znaleziono: {product.name}")

        if product.location_id is None:
            # --- CREATE ---
            print("Ten produkt nie ma jeszcze przypisanej lokalizacji.")

            while True:
                location_code = input("Podaj lokalizację dla tego produktu (Enter, by anulować): ")

                if location_code == "":
                    print("Anulowano - lokalizacja nie została przypisana.")
                    break

                if assign_new_location(session, product, location_code):
                    print(f"Przypisano lokalizację {location_code} do produktu {product.name}")
                    break
                else:
                    print(f"Nie ma takiej lokalizacji: {location_code}. Spróbuj ponownie.")

        else:
            # --- READ (zawsze pokazujemy obecną lokalizację) ---
            current_location = find_location_by_id(session, product.location_id)
            print(f"Obecna lokalizacja: {current_location.code}")

            action = input("Co chcesz zrobić? [P]rzypisz nową / [U]suń / Enter = nic: ")

            if action.upper() == "U":
                remove_location(session, product)
                print(f"Usunięto przypisanie lokalizacji dla produktu {product.name}")
            elif action.upper() == "P":
                while True:
                    new_location_code = input("Podaj nową lokalizację (Enter, by anulować): ")

                    if new_location_code == "":
                        print("Anulowano - lokalizacja nie została zmieniona.")
                        break

                    if update_location(session, product, new_location_code):
                        print(f"Zmieniono lokalizację na {new_location_code}")
                        break
                    else:
                        print(f"Nie ma takiej lokalizacji: {new_location_code}. Spróbuj ponownie.")
            elif action == "":
                print(f"Nic nie zmieniono, obecna lokalizacja to: {current_location.code}")
            else:
                print("Nieznana opcja - wybierz P lub U.")

session.close()