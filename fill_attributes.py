import os

from database.db import SessionLocal
from services.classification_service import (
    set_products_attributes,
    list_products_to_fill,
    group_products_by_hint,
    list_filled_groups,
    list_manufacturers,
    list_categories,
    common_value,
    load_seed_categories,
    merge_options,
    filter_options,
    find_similar,
)
from services.product_service import search_products
from services.selection_service import parse_selection

NO_HINT_LABEL = "bez podpowiedzi producenta"
MAX_SEARCH_RESULTS = 50
MAX_LISTED = 40
CATEGORIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "categories.txt")


def hint_key(hint):
    """Klucz grupy: producenci różniący się tylko wielkością liter to ta sama grupa."""
    return hint.lower() if hint else None


def create_new_value(prompt_text, options):
    """Pyta o nazwę nowej pozycji. Jeśli taka albo bardzo podobna już istnieje (literówka, inna
    wielkość liter), proponuje użycie istniejącej. Zwraca nazwę albo None, gdy anulowano."""
    name = input(prompt_text).strip()
    if name == "":
        return None

    similar = find_similar(name, options)
    if not similar:
        return name

    if similar[0].lower() == name.lower():
        print(f"Taka pozycja już istnieje: {similar[0]}. Używam jej.")
        return similar[0]

    print("Podobne pozycje już istnieją:")
    for number, existing in enumerate(similar, start=1):
        print(f"  {number}. {existing}")
    answer = input("Numer = użyj istniejącej / [T] utwórz nową mimo to / Enter = anuluj: ").strip().upper()
    if answer == "T":
        return name
    if answer.isdigit() and 1 <= int(answer) <= len(similar):
        return similar[int(answer) - 1]
    return None


def choose_value(label, options, new_prompt, default=None):
    """Wybór z listy (producent albo kategoria). Numer wybiera pozycję, wpisany tekst zawęża listę,
    [N] tworzy nową pozycję. Enter wybiera wartość domyślną (a bez niej anuluje).
    Zwraca wybraną wartość albo None, gdy anulowano."""
    shown = options
    while True:
        if not options:
            print("  (lista jest jeszcze pusta, użyj [N], żeby dodać pierwszą pozycję)")
        elif not shown:
            print("  (nic nie pasuje, wpisz inny fragment albo użyj [N])")
        else:
            for number, name in enumerate(shown[:MAX_LISTED], start=1):
                print(f"  {number}. {name}")
            if len(shown) > MAX_LISTED:
                print(f"  ... pokazano {MAX_LISTED} z {len(shown)}, wpisz fragment nazwy, żeby zawęzić")

        enter_label = default if default else "anuluj"
        answer = input(f"{label}: numer / fragment nazwy (szukaj) / [N] nowa / Enter = {enter_label}: ").strip()

        if answer == "":
            return default
        if answer.upper() == "N":
            created = create_new_value(new_prompt, options)
            if created is not None:
                return created
            shown = options
            continue
        if answer.isdigit():
            number = int(answer)
            if 1 <= number <= min(len(shown), MAX_LISTED):
                return shown[number - 1]
            print("Nie ma takiego numeru.")
            continue
        shown = filter_options(options, answer)


def fill_selected(session, products, hint, default_category=None):
    """Wybiera z listy (albo tworzy) producenta i kategorię i ustawia je dla wybranych produktów.
    Enter przy producencie (i kategorii, jeśli podano default_category) zostawia wartość domyślną."""
    print("\nWybrane produkty:")
    for product in products:
        print(f"  {product.code} | {product.name}")

    print("\nProducent:")
    manufacturer = choose_value(
        "Producent", list_manufacturers(session), "Nazwa nowego producenta: ", default=hint
    )
    if manufacturer is None:
        print("Anulowano.")
        return

    print("\nKategoria:")
    categories = merge_options(load_seed_categories(CATEGORIES_FILE), list_categories(session))
    category = choose_value("Kategoria", categories, "Nazwa nowej kategorii: ", default=default_category)
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


def search_menu(session):
    """Szukanie dowolnego produktu (po kodzie, EAN lub słowach z nazwy) i poprawa jego
    producenta i kategorii, niezależnie od stanu i od tego, czy był już zatwierdzony."""
    while True:
        term = input("\nSzukaj po kodzie, EAN lub nazwie (Enter = wróć): ").strip()
        if term == "":
            return

        while True:
            found = search_products(session, term)
            if not found:
                print("Nic nie znaleziono.")
                break

            products = sorted(found, key=lambda p: p.name or "")[:MAX_SEARCH_RESULTS]
            if len(found) > MAX_SEARCH_RESULTS:
                print(f"\nZnaleziono {len(found)} produktów, pokazuję pierwsze {MAX_SEARCH_RESULTS}. "
                      "Wpisz dokładniejsze słowa, żeby zawęzić.")
            else:
                print(f"\nZnaleziono: {len(products)}")

            for number, product in enumerate(products, start=1):
                manufacturer = product.manufacturer or "-"
                category = product.category or "-"
                print(f"{number}. {product.code} | {product.name} | {manufacturer} / {category}")

            answer = input(
                "Numery produktów do poprawy (np. 1,3 lub 2-4) / [W] wszystkie / [B] nowe szukanie: "
            ).strip().upper()

            if answer == "B" or answer == "":
                break

            if answer == "W":
                selected = products
            else:
                indices = parse_selection(answer, len(products))
                if indices is None:
                    print("Nieznana opcja. Przykłady wyboru: 2, 1,3 lub 2-4.")
                    continue
                selected = [products[i] for i in indices]

            current_manufacturer = common_value(
                [p.manufacturer or p.suggested_manufacturer for p in selected]
            )
            current_category = common_value([p.category for p in selected])
            fill_selected(session, selected, current_manufacturer, default_category=current_category)


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
        prompt = "\n[S] szukaj produktu / [Z] pokaż uzupełnione / [K] koniec: "
    else:
        groups = group_products_by_hint(products)
        print(f"\nDo uzupełnienia: {len(products)} produktów (stan WAPRO > 0) bez producenta lub kategorii.")
        print("Grupy według producenta z WAPRO (to tylko podpowiedź):")
        for number, (hint, items) in enumerate(groups, start=1):
            print(f"{number}. {hint or NO_HINT_LABEL} ({len(items)} prod.)")
        prompt = "\nNumer grupy / [S] szukaj produktu / [Z] pokaż już uzupełnione / [K] koniec: "

    answer = input(prompt).strip().upper()

    if answer == "K" or (answer == "" and not groups):
        break
    elif answer == "S":
        search_menu(session)
    elif answer == "Z":
        filled_menu(session)
    elif answer.isdigit() and 1 <= int(answer) <= len(groups):
        group_menu(session, groups[int(answer) - 1][0])
    else:
        print("Nieznana opcja.")

session.close()