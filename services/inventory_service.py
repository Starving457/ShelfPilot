from datetime import date

from database.models import InventoryCount


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