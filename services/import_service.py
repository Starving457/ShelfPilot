from dataclasses import dataclass, field

from database.models import Product


@dataclass
class ImportSummary:
    """Wynik importu z WAPRO (albo jego podglądu)."""

    status: str = "ok"  # "ok" albo "empty_source" (źródło nie zwróciło żadnych artykułów)
    created: int = 0  # nowe produkty
    updated: int = 0  # istniejące produkty, w których coś się zmieniło
    unchanged: int = 0  # istniejące produkty bez zmian
    missing: int = 0  # znane z WAPRO, ale nieobecne tym razem (stan ustawiony jako nieznany)
    conflicts: list = field(default_factory=list)  # kody pominiętych artykułów (kod zajęty przez inny produkt)
    new_products: list = field(default_factory=list)  # nazwy dodanych produktów


def _apply_article(product, article):
    """Przepisuje na produkt tylko to, co należy do WAPRO: identyfikator, kod, nazwę, stan i EAN.
    Pusty EAN z WAPRO nie kasuje EAN wpisanego u nas. Zwraca True, jeśli coś się zmieniło."""
    new_values = {
        "wapro_id": article.wapro_id,
        "code": article.code,
        "name": article.name,
        "wapro_quantity": article.quantity,
    }
    if article.ean is not None:
        new_values["ean"] = article.ean

    changed = False
    for field_name, value in new_values.items():
        if getattr(product, field_name) != value:
            setattr(product, field_name, value)
            changed = True
    return changed


def import_articles(session, articles, apply=True):
    """Wprowadza artykuły z WAPRO (lista WaproArticle) do bazy programu.

    Zasady:
    - produkt rozpoznajemy po wapro_id; produkt dodany ręcznie (bez wapro_id) z tym samym kodem
      zostaje przejęty, a nie zdublowany;
    - nowy produkt czeka na sprawdzenie (producent z WAPRO trafia tylko jako podpowiedź);
    - istniejącemu produktowi zmieniamy tylko kod, nazwę, EAN i stan WAPRO. Lokalizacje, wyniki
      liczeń oraz zatwierdzony producent i kategoria zostają nietknięte;
    - produkt, którego WAPRO tym razem nie zwróciło, zostaje, ale jego stan jest nieznany;
    - artykuł, którego kod zajmuje inny produkt, jest pomijany i trafia do conflicts;
    - apply=False tylko liczy, co by się zmieniło (nic nie zapisuje).
    Zwraca ImportSummary."""
    summary = ImportSummary()

    # Puste źródło to najpewniej błąd ustawień, a nie "cały magazyn zniknął"
    if not articles:
        summary.status = "empty_source"
        return summary

    products = session.query(Product).all()
    by_wapro_id = {p.wapro_id: p for p in products if p.wapro_id is not None}
    by_code = {p.code: p for p in products if p.code is not None}
    seen_ids = set()

    for article in articles:
        seen_ids.add(article.wapro_id)

        product = by_wapro_id.get(article.wapro_id)
        code_owner = by_code.get(article.code)

        # Produkt dodany ręcznie, bez powiązania z WAPRO: przejmujemy go po kodzie
        if product is None and code_owner is not None and code_owner.wapro_id is None:
            product = code_owner

        # Kod zajęty przez inny produkt: nie ryzykujemy pomyłki
        if code_owner is not None and code_owner is not product:
            summary.conflicts.append(article.code)
            continue

        if product is None:
            product = Product(
                wapro_id=article.wapro_id,
                code=article.code,
                ean=article.ean,
                name=article.name,
                wapro_quantity=article.quantity,
            )
            if article.producer:
                product.suggested_manufacturer = article.producer
                product.suggested_source = "wapro"
            session.add(product)
            by_wapro_id[article.wapro_id] = product
            by_code[article.code] = product
            summary.created += 1
            summary.new_products.append(article.name)
            continue

        old_code = product.code
        if _apply_article(product, article):
            if old_code != product.code:
                by_code.pop(old_code, None)
                by_code[product.code] = product
            summary.updated += 1
        else:
            summary.unchanged += 1

    for product in products:
        if (
            product.wapro_id is not None
            and product.wapro_id not in seen_ids
            and product.wapro_quantity is not None
        ):
            product.wapro_quantity = None
            summary.missing += 1

    if apply:
        session.commit()
    else:
        session.rollback()

    return summary