from database.models import Product, Location


def find_location(session, code):
    """Szuka lokalizacji w bazie po jej kodzie. Zwraca obiekt Location albo None."""
    return session.query(Location).filter(Location.code == code).first()


def find_product(session, code):
    """Szuka produktu w bazie po jego kodzie. Zwraca obiekt Product albo None."""
    return session.query(Product).filter(Product.code == code).first()


def find_location_by_id(session, location_id):
    """Szuka lokalizacji w bazie po jej id. Zwraca obiekt Location albo None."""
    return session.query(Location).filter(Location.id == location_id).first()


def assign_new_location(session, product, location_code):
    """Przypisuje lokalizację do produktu, który jej jeszcze nie ma. Zwraca True jeśli się udało, False jeśli lokalizacja nie istnieje."""
    location = find_location(session, location_code)

    if location is None:
        return False

    product.location_id = location.id
    session.commit()
    return True


def update_location(session, product, new_location_code):
    """Zmienia lokalizację produktu na nową. Zwraca True jeśli się udało, False jeśli nowa lokalizacja nie istnieje."""
    new_location = find_location(session, new_location_code)

    if new_location is None:
        return False

    product.location_id = new_location.id
    session.commit()
    return True


def remove_location(session, product):
    """Usuwa przypisanie lokalizacji dla produktu (produkt zostaje, tylko lokalizacja się czyści)."""
    product.location_id = None
    session.commit()