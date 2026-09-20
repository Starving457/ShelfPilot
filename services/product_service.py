from database.models import Product


def search_products(session, search_term):
    """Szuka produktów po dokładnym kodzie, dokładnym EAN, albo po słowach zawartych w nazwie (w dowolnej kolejności).
    Zwraca listę pasujących produktów (może być pusta)."""

    # Najpierw sprawdzamy dokładne dopasowanie po kodzie lub EAN
    exact_matches = session.query(Product).filter(
        (Product.code == search_term) | (Product.ean == search_term)
    ).all()

    if exact_matches:
        return exact_matches

    # Jeśli nic nie pasuje dokładnie, szukamy po słowach w nazwie
    words = search_term.split()

    query = session.query(Product)
    for word in words:
        query = query.filter(Product.name.contains(word))

    return query.all()