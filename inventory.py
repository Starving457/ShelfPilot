from datetime import date

from database.db import SessionLocal
from services.product_service import search_products
from services.selection_service import parse_selection
from services.inventory_service import (
    record_count,
    get_last_count,
    list_groups,
    list_manufacturer_summaries,
    suggest_next_group,
    get_group_products,
    get_group_extras,
    count_products_outside_rotation,
)

STOP = object()  # znacznik "zakończ pętlę po produktach"
BACK = object()  # znacznik "wróć do poprzedniego produktu"


def ask_quantity(prompt, allow_stop=False):
    """Pyta o ilość do skutku. Zwraca liczbę, None (pominięcie), STOP albo BACK."""
    while True:
        text = input(prompt).strip()

        if text == "":
            return None
        if allow_stop and text.upper() == "K":
            return STOP
        if allow_stop and text.upper() == "P":
            return BACK
        if text.isdigit():
            return int(text)

        print("Podaj liczbę całkowitą (0 lub więcej).")


def count_product(session, product, allow_stop=False):
    """Pyta o ilość jednego produktu i zapisuje wynik. Zwraca True, jeśli zapisano,
    False, jeśli pominięto, STOP albo BACK."""
    last = get_last_count(session, product)

    print()
    if last is not None and last.counted_at == date.today():
        print(f"Już policzono dziś: {last.counted_quantity}. Nowy wynik zastąpi poprzedni w raporcie.")

    hint = "Enter = pomiń, P = cofnij, K = zakończ" if allow_stop else "Enter = anuluj"
    quantity = ask_quantity(
        f"{product.code} | {product.name}\nPoliczona ilość ({hint}): ", allow_stop=allow_stop
    )

    if quantity is STOP:
        return STOP
    if quantity is BACK:
        return BACK
    if quantity is None:
        print("Pominięto.")
        return False

    if record_count(session, product, quantity) == "ok":
        print(f"Zapisano: {quantity}")
        return True

    print("Nie udało się zapisać.")
    return False


def describe_status(last):
    """Krótki opis statusu liczenia produktu."""
    if last is None:
        return "nigdy nie liczony"
    if last.counted_at == date.today():
        return f"policzono dziś: {last.counted_quantity}"
    return f"ostatnio: {last.counted_at}"


def choose_number(prompt, count):
    """Pyta o numer z zakresu 1..count. Zwraca indeks (od 0) albo None, gdy nie podano numeru."""
    text = input(prompt).strip()
    if text.isdigit() and 1 <= int(text) <= count:
        return int(text) - 1
    return None


def search_and_count(session):
    """Wyszukuje dowolny produkt (także spoza rotacji) i pozwala go policzyć."""
    term = input("Szukaj po kodzie, EAN lub nazwie (Enter, by wrócić): ")
    if term == "":
        return

    results = search_products(session, term)
    if not results:
        print("Nic nie znaleziono.")
        return

    shown = results[:20]
    for number, product in enumerate(shown, start=1):
        print(f"{number}. {product.code} | {product.name} | stan WAPRO: {product.wapro_quantity}")
    if len(results) > len(shown):
        print(f"(pokazano {len(shown)} z {len(results)}, zawęź wyszukiwanie)")

    index = choose_number("Numer produktu do policzenia (Enter, by wrócić): ", len(shown))
    if index is not None:
        count_product(session, shown[index])


def count_extras(session, group):
    """Lista produktów grupy ze stanem WAPRO 0 (do dopisania, jeśli ktoś je znalazł)."""
    extras = get_group_extras(session, group.manufacturer, group.category)
    if not extras:
        print("Brak produktów ze stanem 0 w tej grupie.")
        return

    print("Produkty ze stanem 0 w WAPRO (liczysz tylko, jeśli je znalazłeś):")
    for number, product in enumerate(extras, start=1):
        print(f"{number}. {product.code} | {product.name}")

    index = choose_number("Numer znalezionego produktu (Enter, by wrócić): ", len(extras))
    if index is not None:
        count_product(session, extras[index])


def count_sequence(session, products):
    """Liczy podane produkty po kolei. P cofa o jeden produkt, K kończy (przy więcej niż jednym)."""
    allow_stop = len(products) > 1
    position = 0
    while position < len(products):
        result = count_product(session, products[position], allow_stop=allow_stop)
        if result is STOP:
            break
        if result is BACK:
            if position > 0:
                position -= 1
            else:
                print("To pierwszy produkt, nie ma do czego wracać.")
        else:
            position += 1


def group_menu(session, group):
    """Liczenie w obrębie jednej grupy. Wynik zapisuje się po każdym produkcie."""
    while True:
        pairs = get_group_products(session, group.manufacturer, group.category)

        print(f"\n=== {group.manufacturer} / {group.category} ===")
        for number, (product, last) in enumerate(pairs, start=1):
            print(f"{number}. {product.code} | {product.name} [{describe_status(last)}]")

        answer = input(
            "Numer(y) produktów (np. 1,3 lub 2-4) / [W] po kolei te nieliczone dziś / "
            "[Z] produkty ze stanem 0 / [B] wróć: "
        ).strip().upper()

        if answer == "B" or answer == "":
            return

        if answer == "W":
            queue = [
                product for product, last in pairs
                if last is None or last.counted_at != date.today()
            ]
            count_sequence(session, queue)
        elif answer == "Z":
            count_extras(session, group)
        else:
            indices = parse_selection(answer, len(pairs))
            if indices is None:
                print("Nieznana opcja. Przykłady wyboru: 2, 1,3 lub 2-4.")
            else:
                count_sequence(session, [pairs[i][0] for i in indices])


def describe_counting(product_count, never_counted_count, oldest_last_count):
    """Krótki opis stanu liczenia grupy albo całego producenta."""
    if never_counted_count == product_count:
        return "jeszcze nie liczono"
    status = f"najstarsze liczenie: {oldest_last_count}"
    if never_counted_count > 0:
        status += f", nieliczonych: {never_counted_count}"
    return status


def manufacturer_menu(session, manufacturer):
    """Wybór kategorii w obrębie jednego producenta."""
    while True:
        groups = [g for g in list_groups(session) if g.manufacturer == manufacturer]
        if not groups:
            return
        suggested = suggest_next_group(session, manufacturer)

        print(f"\n=== {manufacturer} ===")
        print("Kategorie:")
        for number, group in enumerate(groups, start=1):
            mark = "  <- podpowiedź" if group == suggested else ""
            status = describe_counting(
                group.product_count, group.never_counted_count, group.oldest_last_count
            )
            print(f"{number}. {group.category} ({group.product_count} prod., {status}){mark}")

        answer = input("\nNumer kategorii / Enter = podpowiedź / [B] wróć: ").strip().upper()

        if answer == "B":
            return
        elif answer == "":
            group_menu(session, suggested)
        elif answer.isdigit() and 1 <= int(answer) <= len(groups):
            group_menu(session, groups[int(answer) - 1])
        else:
            print("Nieznana opcja.")


def print_manufacturers(manufacturers, suggested_manufacturer):
    print("\nProducenci:")
    for number, item in enumerate(manufacturers, start=1):
        mark = "  <- podpowiedź" if item.manufacturer == suggested_manufacturer else ""
        status = describe_counting(
            item.product_count, item.never_counted_count, item.oldest_last_count
        )
        print(
            f"{number}. {item.manufacturer} "
            f"({item.group_count} kat., {item.product_count} prod., {status}){mark}"
        )


session = SessionLocal()

outside = count_products_outside_rotation(session)
if outside > 0:
    print(f"Uwaga: {outside} produktów ze stanem WAPRO > 0 nie ma kategorii i nie podlega rotacji.")

while True:
    manufacturers = list_manufacturer_summaries(session)
    suggested = suggest_next_group(session)

    if manufacturers:
        print_manufacturers(manufacturers, suggested.manufacturer)
        prompt = "\nNumer producenta / Enter = podpowiedź / [S] szukaj produktu / [K] koniec: "
    else:
        print("\nBrak grup do liczenia (produkty muszą mieć zatwierdzoną kategorię i stan WAPRO > 0).")
        prompt = "\n[S] szukaj produktu / [K] koniec: "

    answer = input(prompt).strip().upper()

    if answer == "K":
        break
    elif answer == "S":
        search_and_count(session)
    elif answer == "" and suggested is not None:
        group_menu(session, suggested)
    elif answer.isdigit() and 1 <= int(answer) <= len(manufacturers):
        manufacturer_menu(session, manufacturers[int(answer) - 1].manufacturer)
    else:
        print("Nieznana opcja.")

session.close()