from database.db import SessionLocal
from services.classification_service import (
    set_products_attributes,
    list_products_to_fill,
    group_products_by_hint,
    list_filled_groups,
    list_manufacturers,
    list_categories,
    resolve_choice,
)
from services.selection_service import parse_selection

NO_HINT_LABEL = "bez podpowiedzi producenta"


def hint_key(hint):
    """Klucz grupy: producenci różniący się tylko wielkością liter to ta sama grupa."""
    return hint.lower() if hint else None


def fill_selected(session, products, hint, default_category=None):
    """Pyta o producenta i kategorię i ustawia je dla wybranych produktów.
    Enter przy producencie (i kategorii, jeśli podano default_category) zostawia podpowiedzianą wartość."""
    print("\nWybrane produkty:")
    for product in products:
        print(f"  {product.code} | {product.name}")

    manufacturers = list_manufacturers(session)
    if manufacturers:
        print("\nIstniejący producenci:")
        for number, name in enumerate(manufacturers, start=1):
            print(f"  {number}. {name}")
        print("Wpisz numer z listy albo nową nazwę.")

    prompt = f"Producent (Enter = {hint}): " if hint else "Producent (Enter = anuluj): "
    manufacturer = resolve_choice(input(prompt), manufacturers)
    if manufacturer is None and hint:
        manufacturer = hint
    if manufacturer is None:
        print("Anulowano.")
        return

    categories = list_categories(session)
    if categories:
        print("\nIstniejące kategorie:")
        for number, name in enumerate(categories, start=1):
            print(f"  {number}. {name}")
        print("Wpisz numer z listy albo nową nazwę.")

    prompt = f"Kategoria (Enter = {default_category}): " if default_category else "Kategoria (Enter = anuluj): "
    category = resolve_choice(input(prompt), categories)
    if category is None and default_category:
        category = default_category
    if category is None:
        print("Anulowano.")
        return

    print(f"\nProducent: {manufacturer}")
    print(f"Kategoria: {category}")
    print(f"Dla produktów: {', '.join(product.name for product in products[:5])}"
          + (f" i {len(products) - 5} innych" if len(products) > 5 else ""))
    answer = input("Zapisać? (T/N): ").strip().upper()
    if answer != "T":
        print("Anulowano.")
        return

    if set_products_attributes(session, products, manufacturer, category) == "ok":
        first = products[0]
        print(f"Zapisano: {first.manufacturer} / {first.category} ({len(products)} produktów).")
    else:
        print("Nie udało się zapisać.")


def group_menu(session, hint):
    """Lista produktów jednej grupy i wybór, którym nadać producenta i kategorię."""
    while True:
        products = [
            p for p in list_products_to_fill(session)
            if hint_key(p.suggested_manufacturer) == hint_key(hint)
        ]
        if not products:
            print("Ta grupa jest już uzupełniona.")
            return

        print(f"\n=== {hint or NO_HINT_LABEL} ({len(products)}) ===")
        for number, product in enumerate(products, start=1):
            print(f"{number}. {product.code} | {product.name}")

        answer = input(
            "Numery produktów (np. 1,3 lub 2-4) / [W] wszystkie / [B] wróć: "
        ).strip().upper()

        if answer == "B" or answer == "":
            return

        if answer == "W":
            selected = products
        else:
            indices = parse_selection(answer, len(products))
            if indices is None:
                print("Nieznana opcja. Przykłady wyboru: 2, 1,3 lub 2-4.")
                continue
            selected = [products[i] for i in indices]

        fill_selected(session, selected, hint)


def filled_group_menu(session, manufacturer, category):
    """Produkty jednej już uzupełnionej grupy; pozwala je poprawić (zmienić producenta lub kategorię)."""
    while True:
        products = next(
            (
                items
                for group_manufacturer, group_category, items in list_filled_groups(session)
                if group_manufacturer == manufacturer and group_category == category
            ),
            [],
        )
        if not products:
            print("Ta grupa jest już pusta.")
            return

        print(f"\n=== {manufacturer} / {category} ({len(products)}) ===")
        for number, product in enumerate(products, start=1):
            print(f"{number}. {product.code} | {product.name}")

        answer = input(
            "Numery produktów do poprawy (np. 1,3 lub 2-4) / [W] wszystkie / [B] wróć: "
        ).strip().upper()

        if answer == "B" or answer == "":
            return

        if answer == "W":
            selected = products
        else:
            indices = parse_selection(answer, len(products))
            if indices is None:
                print("Nieznana opcja. Przykłady wyboru: 2, 1,3 lub 2-4.")
                continue
            selected = [products[i] for i in indices]

        fill_selected(session, selected, manufacturer, default_category=category)


def filled_menu(session):
    """Już uzupełnione produkty: grupy producent / kategoria, z możliwością poprawy."""
    while True:
        groups = list_filled_groups(session)
        if not groups:
            print("Nic jeszcze nie uzupełniono.")
            return

        print("\nJuż uzupełnione (producent / kategoria):")
        for number, (manufacturer, category, items) in enumerate(groups, start=1):
            print(f"{number}. {manufacturer} / {category} ({len(items)} prod.)")

        answer = input("\nNumer grupy, by poprawić jej produkty / [B] wróć: ").strip().upper()

        if answer == "B" or answer == "":
            return
        elif answer.isdigit() and 1 <= int(answer) <= len(groups):
            manufacturer, category, _ = groups[int(answer) - 1]
            filled_group_menu(session, manufacturer, category)
        else:
            print("Nieznana opcja.")


session = SessionLocal()

while True:
    products = list_products_to_fill(session)
    if not products:
        print("Wszystkie produkty ze stanem WAPRO większym od zera mają producenta i kategorię.")
        print("Możesz jeszcze przejrzeć i poprawić uzupełnione.")
        groups = []
        prompt = "\n[Z] pokaż uzupełnione / [K] koniec: "
    else:
        groups = group_products_by_hint(products)
        print(f"\nDo uzupełnienia: {len(products)} produktów (stan WAPRO > 0) bez producenta lub kategorii.")
        print("Grupy według producenta z WAPRO (to tylko podpowiedź):")
        for number, (hint, items) in enumerate(groups, start=1):
            print(f"{number}. {hint or NO_HINT_LABEL} ({len(items)} prod.)")
        prompt = "\nNumer grupy / [Z] pokaż już uzupełnione / [K] koniec: "

    answer = input(prompt).strip().upper()

    if answer == "K" or (answer == "" and not groups):
        break
    elif answer == "Z":
        filled_menu(session)
    elif answer.isdigit() and 1 <= int(answer) <= len(groups):
        group_menu(session, groups[int(answer) - 1][0])
    else:
        print("Nieznana opcja.")

session.close()