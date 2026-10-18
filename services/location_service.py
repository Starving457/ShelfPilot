from database.models import Product, Location, ProductLocation


def find_location(session, code):
    """Szuka lokalizacji w bazie po jej kodzie. Zwraca obiekt Location albo None."""
    return session.query(Location).filter(Location.code == code).first()


def find_product(session, code):
    """Szuka produktu w bazie po jego kodzie. Zwraca obiekt Product albo None."""
    return session.query(Product).filter(Product.code == code).first()


def _find_link(session, product, location):
    """Pomocnicza: szuka wpisu 'produkt leży na półce'. Zwraca ProductLocation albo None."""
    return (
        session.query(ProductLocation)
        .filter(
            ProductLocation.product_id == product.id,
            ProductLocation.location_id == location.id,
        )
        .first()
    )


def get_product_locations(session, product):
    """Zwraca listę lokalizacji (obiektów Location), na których leży produkt.
    Pusta lista, jeśli produkt nie jest nigdzie przypisany."""
    return (
        session.query(Location)
        .join(ProductLocation, ProductLocation.location_id == Location.id)
        .filter(ProductLocation.product_id == product.id)
        .all()
    )


def find_products_by_location(session, location_code):
    """Zwraca listę produktów leżących na danej półce.
    Pusta lista, jeśli półka nie istnieje albo nic na niej nie leży."""
    location = find_location(session, location_code)

    if location is None:
        return []

    return (
        session.query(Product)
        .join(ProductLocation, ProductLocation.product_id == Product.id)
        .filter(ProductLocation.location_id == location.id)
        .all()
    )


def add_product_to_location(session, product, location_code):
    """Dodaje produkt na podaną półkę.
    Zwraca: "ok", "location_not_found" albo "already_assigned"."""
    location = find_location(session, location_code)

    if location is None:
        return "location_not_found"

    if _find_link(session, product, location) is not None:
        return "already_assigned"

    session.add(ProductLocation(product_id=product.id, location_id=location.id))
    session.commit()
    return "ok"


def remove_product_from_location(session, product, location_code):
    """Usuwa przypisanie produktu do półki (sam produkt zostaje w bazie).
    Zwraca: "ok", "location_not_found" albo "not_assigned"."""
    location = find_location(session, location_code)

    if location is None:
        return "location_not_found"

    link = _find_link(session, product, location)

    if link is None:
        return "not_assigned"

    session.delete(link)
    session.commit()
    return "ok"


def move_product_location(session, product, from_code, to_code):
    """Przenosi produkt z jednej półki na drugą.
    Zwraca: "ok", "location_not_found", "not_assigned" (produkt nie leży na półce
    źródłowej) albo "already_assigned" (produkt już leży na docelowej)."""
    from_location = find_location(session, from_code)
    to_location = find_location(session, to_code)

    if from_location is None or to_location is None:
        return "location_not_found"

    link = _find_link(session, product, from_location)

    if link is None:
        return "not_assigned"

    if _find_link(session, product, to_location) is not None:
        return "already_assigned"

    link.location_id = to_location.id
    session.commit()
    return "ok"

def create_location(session, rack, shelf):
    """Tworzy nową lokalizację. Kod powstaje z regału i półki (np. 'A' + '1' = 'A1').
    Zwraca: "ok" albo "already_exists"."""
    code = rack + shelf

    if find_location(session, code) is not None:
        return "already_exists"

    session.add(Location(code=code, rack=rack, shelf=shelf))
    session.commit()
    return "ok"


def delete_location(session, location_code):
    """Usuwa lokalizację, ale tylko jeśli nic na niej nie leży.
    Zwraca: "ok", "location_not_found" albo "has_products"."""
    location = find_location(session, location_code)

    if location is None:
        return "location_not_found"

    link = (
        session.query(ProductLocation)
        .filter(ProductLocation.location_id == location.id)
        .first()
    )

    if link is not None:
        return "has_products"

    session.delete(location)
    session.commit()
    return "ok"