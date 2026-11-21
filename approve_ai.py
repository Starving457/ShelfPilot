from database.db import SessionLocal
from services.classification_service import (
    approve_suggestions,
    confidence_of,
    list_products_to_fill,
    list_suggestion_groups,
    reject_suggestions,
)
from services.selection_service import parse_selection

CONFIDENCE_LABELS = {"high": "", "medium": "  [średnia pewność]", "low": "  [niska pewność]"}


def count_levels(items):
    """Zwraca (liczba pewnych, liczba do sprawdzenia) dla listy produktów."""
    levels = [confidence_of(product) for product in items]
    sure = levels.count("high")
    return sure, len(levels) - sure


def find_group(session, manufacturer, category):
    """Szuka grupy po producencie i kategorii (bez względu na wielkość liter)."""
    for group_manufacturer, group_category, items in list_suggestion_groups(session):
        if group_manufacturer.lower() == manufacturer.lower() and group_category.lower() == category.lower():
            return items
    return []


def group_menu(session, manufacturer, category):
    """Produkty jednej grupy podpowiedzi: zatwierdź albo odrzuć całość lub wybrane."""
    while True:
        items = find_group(session, manufacturer, category)
        if not items:
            print("Ta grupa jest już rozpatrzona.")
            return

        print(f"\n=== {manufacturer} / {category} ({len(items)}) ===")
        for number, product in enumerate(items, start=1):
            label = CONFIDENCE_LABELS[confidence_of(product)]
            print(f"{number}. {product.code} | {product.name}{label}")

        answer = input(
            "[T] zatwierdź wszystkie / [R] odrzuć wszystkie / numery (np. 1,3 lub 2-4) wybrane / [B] wróć: "
        ).strip().upper()

        if answer == "B" or answer == "":
            return
        elif answer == "T":
            print(f"Zatwierdzono: {approve_suggestions(session, items)} produktów.")
        elif answer == "R":
            print(f"Odrzucono: {reject_suggestions(session, items)} produktów (wrócą na listę do uzupełnienia).")
        else:
            indices = parse_selection(answer, len(items))
            if indices is None:
                print("Nieznana opcja. Przykłady wyboru: 2, 1,3 lub 2-4.")
                continue
            selected = [items[i] for i in indices]
            action = input(f"Dla {len(selected)} wybranych: [T] zatwierdź / [R] odrzuć / [B] anuluj: ").strip().upper()
            if action == "T":
                print(f"Zatwierdzono: {approve_suggestions(session, selected)} produktów.")
            elif action == "R":
                print(f"Odrzucono: {reject_suggestions(session, selected)} produktów.")
            else:
                print("Anulowano.")


def approve_all_sure(session):
    """Zatwierdza naraz wszystkie grupy, w których każdy produkt ma wysoką pewność."""
    sure_products = []
    for _, _, items in list_suggestion_groups(session):
        if count_levels(items)[1] == 0:
            sure_products.extend(items)

    if not sure_products:
        print("Nie ma grup z samymi pewnymi podpowiedziami.")
        return

    answer = input(f"Zatwierdzić {len(sure_products)} produktów z grup z samą wysoką pewnością? (T/N): ").strip().upper()
    if answer == "T":
        print(f"Zatwierdzono: {approve_suggestions(session, sure_products)} produktów.")
    else:
        print("Anulowano.")


session = SessionLocal()
only_to_check = False

while True:
    groups = list_suggestion_groups(session)
    if only_to_check:
        groups = [group for group in groups if count_levels(group[2])[1] > 0]

    total = sum(len(items) for _, _, items in groups)
    if not groups:
        print("\nNie ma podpowiedzi AI do rozpatrzenia.")
        left = len(list_products_to_fill(session))
        if left:
            print(f"Do uzupełnienia zostało {left} produktów: python export_for_ai.py albo python fill_attributes.py")
        break

    title = "Do sprawdzenia" if only_to_check else "Podpowiedzi AI"
    print(f"\n{title}: {total} produktów w {len(groups)} grupach.")
    for number, (manufacturer, category, items) in enumerate(groups, start=1):
        sure, to_check = count_levels(items)
        note = f"  [do sprawdzenia: {to_check}]" if to_check else ""
        print(f"{number}. {manufacturer} / {category} ({len(items)} prod.){note}")

    toggle = "wszystkie grupy" if only_to_check else "tylko do sprawdzenia"
    answer = input(
        f"\nNumer grupy / [A] zatwierdź wszystkie grupy z samymi pewnymi / [P] pokaż {toggle} / [K] koniec: "
    ).strip().upper()

    if answer == "K" or answer == "":
        break
    elif answer == "A":
        approve_all_sure(session)
    elif answer == "P":
        only_to_check = not only_to_check
    elif answer.isdigit() and 1 <= int(answer) <= len(groups):
        manufacturer, category, _ = groups[int(answer) - 1]
        group_menu(session, manufacturer, category)
    else:
        print("Nieznana opcja.")

session.close()