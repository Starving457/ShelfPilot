from database.models import Product


def _clean(text):
    """Pomocnicza: obcina spacje. Zwraca None, jeśli tekst jest pusty albo to nie tekst."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    return text if text != "" else None


def resolve_choice(text, options):
    """Zamienia wpisany tekst na wybraną wartość.
    Numer z listy options (liczony od 1) wybiera istniejącą pozycję, każdy inny tekst to nowa nazwa.
    Zwraca wybraną wartość albo None, jeśli nic nie wpisano."""
    text = _clean(text)
    if text is None:
        return None
    if text.isdigit() and 1 <= int(text) <= len(options):
        return options[int(text) - 1]
    return text


def _canonical(session, column, text):
    """Pomocnicza: jeśli taka sama wartość (bez względu na wielkość liter) jest już używana,
    zwraca jej zapisaną postać. Dzięki temu "vortex" i "Vortex" nie staną się dwoma producentami."""
    rows = session.query(column).filter(column.isnot(None)).distinct().all()
    for existing in sorted(row[0] for row in rows):
        if existing.lower() == text.lower():
            return existing
    return text


def set_products_attributes(session, products, manufacturer, category):
    """Ręcznie ustawia ten sam producent i kategorię dla wielu produktów naraz.
    Wynik jest od razu zatwierdzony, a podpowiedzi znikają. Jeśli taki producent albo kategoria
    jest już w bazie (inna wielkość liter), używana jest istniejąca pisownia.
    Zwraca: "ok" albo "invalid" (pusty producent lub kategoria)."""
    manufacturer = _clean(manufacturer)
    category = _clean(category)

    if manufacturer is None or category is None:
        return "invalid"

    manufacturer = _canonical(session, Product.manufacturer, manufacturer)
    category = _canonical(session, Product.category, category)

    for product in products:
        product.manufacturer = manufacturer
        product.category = category
        product.classification_source = "manual"
        product.review_status = "confirmed"
        product.suggested_manufacturer = None
        product.suggested_category = None
        product.suggested_source = None

    session.commit()
    return "ok"


def set_product_attributes(session, product, manufacturer, category):
    """Ręcznie ustawia producenta i kategorię jednego produktu (także poprawia wcześniejszą pomyłkę).
    Zwraca: "ok" albo "invalid" (pusty producent lub kategoria)."""
    return set_products_attributes(session, [product], manufacturer, category)


def list_products_to_fill(session):
    """Zwraca produkty ze stanem WAPRO większym od zera, którym brakuje zatwierdzonego producenta
    lub kategorii (więc nie wchodzą do rotacji). Kolejność: według podpowiedzianego producenta
    (bez podpowiedzi na końcu), potem według nazwy."""
    products = (
        session.query(Product)
        .filter(
            Product.wapro_quantity > 0,
            (Product.review_status != "confirmed")
            | Product.manufacturer.is_(None)
            | Product.category.is_(None),
        )
        .all()
    )
    return sorted(
        products,
        key=lambda p: (
            p.suggested_manufacturer is None,
            (p.suggested_manufacturer or "").lower(),
            p.name or "",
        ),
    )


def group_products_by_hint(products):
    """Grupuje produkty po podpowiedzianym producencie (np. z pola Producent w WAPRO).
    Zwraca listę par (podpowiedź, produkty) alfabetycznie; grupa bez podpowiedzi (None) jest ostatnia.
    Producentów różniących się tylko wielkością liter traktuje jak jednego."""
    groups = {}
    labels = {}
    for product in products:
        hint = product.suggested_manufacturer
        key = hint.lower() if hint else None
        labels.setdefault(key, hint)
        groups.setdefault(key, []).append(product)

    ordered = sorted(groups, key=lambda key: (key is None, key or ""))
    return [(labels[key], groups[key]) for key in ordered]


def list_filled_groups(session):
    """Zwraca produkty z zatwierdzonym producentem i kategorią jako listę trójek
    (producent, kategoria, produkty), alfabetycznie. Produkty w grupie są posortowane po nazwie."""
    products = (
        session.query(Product)
        .filter(
            Product.review_status == "confirmed",
            Product.manufacturer.isnot(None),
            Product.category.isnot(None),
        )
        .all()
    )

    groups = {}
    for product in products:
        groups.setdefault((product.manufacturer, product.category), []).append(product)

    ordered = sorted(groups, key=lambda key: (key[0].lower(), key[1].lower()))
    return [
        (manufacturer, category, sorted(groups[(manufacturer, category)], key=lambda p: p.name or ""))
        for manufacturer, category in ordered
    ]


def list_manufacturers(session):
    """Zwraca posortowaną listę używanych (zatwierdzonych) producentów."""
    rows = (
        session.query(Product.manufacturer)
        .filter(Product.manufacturer.isnot(None))
        .distinct()
        .all()
    )
    return sorted(r[0] for r in rows)


def list_categories(session):
    """Zwraca posortowaną listę używanych (zatwierdzonych) kategorii."""
    rows = (
        session.query(Product.category)
        .filter(Product.category.isnot(None))
        .distinct()
        .all()
    )
    return sorted(r[0] for r in rows)