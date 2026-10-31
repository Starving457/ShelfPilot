from database.models import Product


def _clean(text):
    """Pomocnicza: obcina spacje. Zwraca None, jeśli tekst jest pusty albo to nie tekst."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    return text if text != "" else None


def set_product_attributes(session, product, manufacturer, category):
    """Ręcznie ustawia producenta i kategorię (także poprawia wcześniejszą pomyłkę).
    Wynik jest od razu zatwierdzony, a podpowiedź (jeśli była) znika.
    Zwraca: "ok" albo "invalid" (pusty producent lub kategoria)."""
    manufacturer = _clean(manufacturer)
    category = _clean(category)

    if manufacturer is None or category is None:
        return "invalid"

    product.manufacturer = manufacturer
    product.category = category
    product.classification_source = "manual"
    product.review_status = "confirmed"
    product.suggested_manufacturer = None
    product.suggested_category = None
    product.suggested_source = None
    session.commit()
    return "ok"


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