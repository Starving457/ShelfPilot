from dataclasses import dataclass
from datetime import date

from database.models import Product, InventoryCount


@dataclass
class GroupSummary:
    """Podsumowanie grupy produktów (producent + kategoria)."""

    manufacturer: str
    category: str
    product_count: int
    never_counted_count: int
    oldest_last_count: date  # najstarsza "ostatnia data liczenia" wśród policzonych produktów (albo None)
    last_counted: date  # najnowsza data liczenia w grupie (albo None)


def record_count(session, product, quantity, counted_at=None):
    """Zapisuje policzoną ilość produktu jako nowy wpis w historii.
    Razem z wynikiem zapisuje stan WAPRO z tej chwili (WAPRO zmienia się po sprzedaży).
    Działa też dla produktu, który w WAPRO ma stan 0 (znaleziony, a WAPRO mówi 0).
    Zwraca: "ok" albo "invalid_quantity" (ilość musi być liczbą całkowitą, 0 lub więcej)."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        return "invalid_quantity"

    entry = InventoryCount(
        product_id=product.id,
        counted_at=counted_at or date.today(),
        counted_quantity=quantity,
        wapro_quantity=product.wapro_quantity,
    )
    session.add(entry)
    session.commit()
    return "ok"


def get_last_count(session, product):
    """Zwraca ostatni wpis liczenia produktu (InventoryCount) albo None, jeśli nigdy nie liczony.
    Jeśli produkt liczono kilka razy tego samego dnia, wygrywa późniejszy wpis."""
    return (
        session.query(InventoryCount)
        .filter(InventoryCount.product_id == product.id)
        .order_by(InventoryCount.counted_at.desc(), InventoryCount.id.desc())
        .first()
    )


def _last_counts_by_product(session):
    """Pomocnicza: słownik {id produktu: ostatni wpis liczenia}."""
    entries = (
        session.query(InventoryCount)
        .order_by(InventoryCount.counted_at, InventoryCount.id)
        .all()
    )
    # Późniejsze wpisy nadpisują wcześniejsze, więc zostaje ostatni
    return {entry.product_id: entry for entry in entries}


def _rotation_products(session):
    """Pomocnicza: produkty podlegające rotacji, czyli zatwierdzony producent i kategoria
    oraz stan WAPRO większy od zera."""
    return (
        session.query(Product)
        .filter(
            Product.review_status == "confirmed",
            Product.manufacturer.isnot(None),
            Product.category.isnot(None),
            Product.wapro_quantity > 0,
        )
        .all()
    )


def list_groups(session):
    """Zwraca listę grup (GroupSummary) posortowaną po producencie i kategorii."""
    last_counts = _last_counts_by_product(session)

    members = {}
    for product in _rotation_products(session):
        members.setdefault((product.manufacturer, product.category), []).append(product)

    groups = []
    for (manufacturer, category), products in members.items():
        dates = [
            last_counts[p.id].counted_at for p in products if p.id in last_counts
        ]
        groups.append(
            GroupSummary(
                manufacturer=manufacturer,
                category=category,
                product_count=len(products),
                never_counted_count=len(products) - len(dates),
                oldest_last_count=min(dates) if dates else None,
                last_counted=max(dates) if dates else None,
            )
        )

    return sorted(groups, key=lambda g: (g.manufacturer, g.category))


def suggest_next_group(session):
    """Podpowiada, którą grupę liczyć dziś. Zwraca GroupSummary albo None, jeśli nie ma grup.
    Kolejność: najpierw grupy z produktem nigdy nieliczonym (w tym grupy całkiem nieliczone),
    potem według najstarszej daty liczenia. Remis rozstrzyga kolejność alfabetyczna."""
    groups = list_groups(session)

    if not groups:
        return None

    def priority(group):
        return (
            0 if group.never_counted_count > 0 else 1,
            group.oldest_last_count or date.min,
            group.manufacturer,
            group.category,
        )

    return min(groups, key=priority)


def get_group_products(session, manufacturer, category):
    """Zwraca produkty grupy jako listę par (produkt, ostatnie liczenie albo None),
    posortowaną po nazwie. Dzięki temu widać, co już policzono (np. po przerwanym liczeniu)."""
    last_counts = _last_counts_by_product(session)

    products = [
        p
        for p in _rotation_products(session)
        if p.manufacturer == manufacturer and p.category == category
    ]
    products.sort(key=lambda p: p.name or "")

    return [(p, last_counts.get(p.id)) for p in products]


def count_products_outside_rotation(session):
    """Zwraca, ile produktów ze stanem WAPRO większym od zera nie ma zatwierdzonej kategorii,
    więc nie wchodzi do żadnej grupy (i nie będzie liczonych w rotacji)."""
    return (
        session.query(Product)
        .filter(
            Product.wapro_quantity > 0,
            (Product.review_status != "confirmed")
            | Product.manufacturer.is_(None)
            | Product.category.is_(None),
        )
        .count()
    )