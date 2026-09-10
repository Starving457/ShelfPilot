from database.db import SessionLocal
from database.models import Product, Location

session = SessionLocal()

code_to_find = input("Podaj kod produktu: ")

product = session.query(Product).filter(Product.code == code_to_find).first()

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

            location = session.query(Location).filter(Location.code == location_code).first()

            if location is None:
                print(f"Nie ma takiej lokalizacji: {location_code}. Spróbuj ponownie.")
            else:
                product.location_id = location.id
                session.commit()
                print(f"Przypisano lokalizację {location.code} do produktu {product.name}")
                break

    else:
        # --- READ (zawsze pokazujemy obecną lokalizację) ---
        current_location = session.query(Location).filter(Location.id == product.location_id).first()
        print(f"Obecna lokalizacja: {current_location.code}")

        # Dopiero TERAZ pytamy, co dalej - z opcją "nic"
        action = input("Co chcesz zrobić? [P]rzypisz nową / [U]suń / Enter = nic: ")

        if action.upper() == "U":
            product.location_id = None
            session.commit()
            print(f"Usunięto przypisanie lokalizacji dla produktu {product.name}")
        elif action.upper() == "P":
            while True:
                new_location_code = input("Podaj nową lokalizację (Enter, by anulować): ")

                if new_location_code == "":
                    print("Anulowano - lokalizacja nie została zmieniona.")
                    break

                new_location = session.query(Location).filter(Location.code == new_location_code).first()

                if new_location is None:
                    print(f"Nie ma takiej lokalizacji: {new_location_code}. Spróbuj ponownie.")
                else:
                    product.location_id = new_location.id
                    session.commit()
                    print(f"Zmieniono lokalizację na {new_location.code}")
                    break
        elif action == "":
            # Użytkownik nacisnął samo Enter - nic nie robimy
            print(f"Nic nie zmieniono, obecna lokalizacja to: {current_location.code}")
        else:
            print("Nieznana opcja - wybierz P lub U.")

session.close()