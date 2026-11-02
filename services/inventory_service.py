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


@dataclass
class ManufacturerSummary:
    """Podsumowanie producenta: wszystkie jego grupy (kategorie) razem."""

    manufacturer: str
    group_count: int
    product_count: int
    never_counted_count: int
    oldest_last_count: date  # najstarsza "ostatnia data liczenia" wśród policzonych produktów (albo None)


@dataclass
class ReportLine:
    """Jedna pozycja raportu: wynik liczenia produktu zestawiony ze stanem WAPRO z chwili liczenia."""

    product: Product
    counted_quantity: int
    wapro_quantity: int  # stan WAPRO zapisany przy liczeniu (albo None)
    difference: int  # policzone minus WAPRO (albo None, gdy stan WAPRO był nieznany)
    is_extra: bool  # znaleziony produkt, który w WAPRO miał stan 0


@dataclass
class GroupCoverage:
    """Ile produktów grupy policzono w danym dniu."""

    manufacturer: str
    category: str
    counted: int
    total: int


@dataclass
class DayReport:
    """Raport rozbieżności za jeden dzień."""

    day: date
    lines: list  # pozycje z różnicą (lub z nieznanym stanem WAPRO), od największej różnicy
    counted_products: int
    matching: int
    shortages: int
    surpluses: int
    unknown_wapro: int
    net_difference: int  # suma różnic w sztukach
    coverage: list  # lista GroupCoverage


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


def list_manufacturer_summaries(session):
    """Zwraca listę producentów (ManufacturerSummary) posortowaną alfabetycznie."""
    by_manufacturer = {}
    for group in list_groups(session):
        by_manufacturer.setdefault(group.manufacturer, []).append(group)

    summaries = []
    for manufacturer, groups in by_manufacturer.items():
        dates = [g.oldest_last_count for g in groups if g.oldest_last_count is not None]
        summaries.append(
            ManufacturerSummary(
                manufacturer=manufacturer,
                group_count=len(groups),
                product_count=sum(g.product_count for g in groups),
                never_counted_count=sum(g.never_counted_count for g in groups),
                oldest_last_count=min(dates) if dates else None,
            )
        )

    return sorted(summaries, key=lambda m: m.manufacturer)


def suggest_next_group(session, manufacturer=None):
    """Podpowiada, którą grupę liczyć dziś. Zwraca GroupSummary albo None, jeśli nie ma grup.
    Kolejność: najpierw grupy z produktem nigdy nieliczonym (w tym grupy całkiem nieliczone),
    potem według najstarszej daty liczenia. Remis rozstrzyga kolejność alfabetyczna.
    Podanie producenta ogranicza wybór do jego grup."""
    groups = list_groups(session)
    if manufacturer is not None:
        groups = [g for g in groups if g.manufacturer == manufacturer]

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


def get_group_extras(session, manufacturer, category):
    """Zwraca produkty grupy, które w WAPRO mają stan 0, posortowane po nazwie.
    To lista 'może się zdarzyć': produkty spoza rotacji, które pracownik może znaleźć
    na półce i dopisać przez record_count. Nie wpływają na postęp grupy."""
    return (
        session.query(Product)
        .filter(
            Product.review_status == "confirmed",
            Product.manufacturer == manufacturer,
            Product.category == category,
            Product.wapro_quantity == 0,
        )
        .order_by(Product.name)
        .all()
    )


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


def get_day_report(session, day, manufacturer=None, category=None):
    """Buduje raport rozbieżności za dany dzień (obiekt DayReport).
    Dla każdego produktu bierze jego ostatnie liczenie z tego dnia i porównuje policzoną
    ilość ze stanem WAPRO zapisanym w chwili liczenia. Opcjonalnie zawęża do producenta
    i/lub kategorii. Pokrycie pokazuje, ile produktów każdej grupy policzono tego dnia."""
    entries = (
        session.query(InventoryCount)
        .filter(InventoryCount.counted_at == day)
        .order_by(InventoryCount.id)
        .all()
    )
    last_by_product = {entry.product_id: entry for entry in entries}

    products = {}
    if last_by_product:
        found = session.query(Product).filter(Product.id.in_(list(last_by_product))).all()
        products = {product.id: product for product in found}

    all_lines = []
    for product_id, entry in last_by_product.items():
        product = products[product_id]

        if manufacturer is not None and product.manufacturer != manufacturer:
            continue
        if category is not None and product.category != category:
            continue

        if entry.wapro_quantity is None:
            difference = None
        else:
            difference = entry.counted_quantity - entry.wapro_quantity

        all_lines.append(
            ReportLine(
                product=product,
                counted_quantity=entry.counted_quantity,
                wapro_quantity=entry.wapro_quantity,
                difference=difference,
                is_extra=entry.wapro_quantity == 0 and entry.counted_quantity > 0,
            )
        )

    known = [line for line in all_lines if line.difference is not None]
    report_lines = [line for line in all_lines if line.difference != 0]
    # Największa różnica (bezwzględna) pierwsza, nieznane stany WAPRO na końcu
    report_lines.sort(
        key=lambda line: (
            line.difference is None,
            -abs(line.difference or 0),
            line.product.name or "",
        )
    )

    # Pokrycie grup: ile produktów (z rotacji) każdej grupy policzono tego dnia
    counted_ids = {line.product.id for line in all_lines}
    group_members = {}
    for product in _rotation_products(session):
        group_members.setdefault((product.manufacturer, product.category), []).append(product)

    coverage = []
    for (group_manufacturer, group_category), members in group_members.items():
        if manufacturer is not None and group_manufacturer != manufacturer:
            continue
        if category is not None and group_category != category:
            continue
        counted_here = sum(1 for member in members if member.id in counted_ids)
        if counted_here > 0:
            coverage.append(
                GroupCoverage(group_manufacturer, group_category, counted_here, len(members))
            )
    coverage.sort(key=lambda c: (c.manufacturer, c.category))

    return DayReport(
        day=day,
        lines=report_lines,
        counted_products=len(all_lines),
        matching=sum(1 for line in known if line.difference == 0),
        shortages=sum(1 for line in known if line.difference < 0),
        surpluses=sum(1 for line in known if line.difference > 0),
        unknown_wapro=len(all_lines) - len(known),
        net_difference=sum(line.difference for line in known),
        coverage=coverage,
    )