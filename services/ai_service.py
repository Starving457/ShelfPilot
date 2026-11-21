import re
from dataclasses import dataclass

from database.models import Product

# Pewność podpowiedzi AI zapisujemy w polu suggested_source, np. "ai-high"
SOURCE_PREFIX = "ai-"
CONFIDENCE_CODES = {"W": "high", "S": "medium", "N": "low"}

PROMPT_INTRO = """Jesteś asystentem magazynu sklepu z optyką, sprzętem foto i wideo oraz wyposażeniem strzeleckim.
Dla każdego produktu z listy na końcu określ PRODUCENTA (markę) i KATEGORIĘ.
Każdy wiersz listy to osobny produkt."""

PROMPT_RULES = """ZASADY
- Producent: nazwa marki tak, jak występuje w nazwie produktu, w zwykłej pisowni (np. Vortex, Swarovski, Vector Optics, Sony, K&F Concept). Skróty zostaw wielkimi literami (PGD, DJI). Ta sama marka musi być zawsze napisana tak samo. Trzecia kolumna listy ("podpowiedź") to producent z systemu magazynowego, bywa błędna, traktuj ją tylko jako wskazówkę. Jeśli w nazwie jest "Producent: X" (broń), weź X. Gdy marki nie da się ustalić, wpisz ?.
- Kategoria: numer z listy kategorii. Jeśli żadna nie pasuje, wybierz numer kategorii "Inne". Nie wymyślaj nowych kategorii.
- Pewność: W = wysoka (nazwa jednoznaczna), S = średnia, N = niska (zgaduję).

GRANICE MIĘDZY KATEGORIAMI
- Jedna liczba z "x" (np. 10x42) to lornetka. Zakres (np. 3-24x56, 1-6x24) to luneta celownicza. Luneta obserwacyjna to np. 20-60x80, "LUNETA", Kowa TSN, Swarovski ATX/STX.
- Słowa "kolimator", "red dot", "holograficzny" to Kolimatory. Powiększalnik (magnifier) to osobna kategoria.
- HIKMICRO Falcon, Condor, Alpex i inne z "KAMERA" w nazwie to celowniki termowizyjne, nie aparaty. Lornetki i monokulary termowizyjne to "Monokulary i termowizory obserwacyjne". Nasadki (np. Thunder) to nasadki.
- Akumulatory i ładowarki zawsze do Akumulatorów (także do latarek). Baterie i akcesoria do dronów DJI do Dronów.
- Timery, bipody, magazynki, chronografy i etui na timery to Akcesoria strzeleckie.
- Moduły laserowe i iluminatory to Iluminatory i lasery. Osłony na szkło, pokrowce na lornetki i lunety, muszle oczne, zakrywki, paski do lornetek, adaptery do nasadek to Akcesoria do optyki.
- Mikrofony, kable, filtry foto, uchwyty i klatki do kamer to Akcesoria foto i wideo.
- Repliki ASG i wiatrówki to Broń, kulki do ASG i wiatrówek to Amunicja.
- Kamizelki balistyczne i taktyczne, hełmy, wkłady balistyczne i ładownice to Kamizelki, hełmy i oporządzenie taktyczne. Zwykła odzież (np. kamizelka puchowa) to Inne.

FORMAT ODPOWIEDZI
Odpowiedz wyłącznie wierszami w formacie:
id;producent;numer_kategorii;pewność
Na przykład:
1234;Vortex;1;W
Jeden wiersz na produkt, każde id dokładnie raz, bez nagłówka, bez komentarzy, bez dodatkowego tekstu."""


@dataclass
class Suggestion:
    """Jedna podpowiedź AI do jednego produktu."""

    product_id: int
    manufacturer: str  # albo None
    category: str  # albo None
    confidence: str  # "high", "medium" albo "low"


@dataclass
class ApplyResult:
    """Wynik zapisania podpowiedzi AI."""

    applied: int = 0
    unknown_id: int = 0  # w bazie nie ma produktu o takim id
    already_confirmed: int = 0  # produkt jest już zatwierdzony, nie ruszamy go
    duplicates: int = 0  # to samo id pojawiło się więcej niż raz (liczy się ostatni wiersz)


def select_products_for_export(session, limit=None):
    """Zwraca produkty ze stanem WAPRO > 0, którym brakuje zatwierdzonego producenta lub kategorii
    i które nie mają jeszcze podpowiedzi AI. Kolejność: według id."""
    products = (
        session.query(Product)
        .filter(
            Product.wapro_quantity > 0,
            (Product.review_status != "confirmed")
            | Product.manufacturer.is_(None)
            | Product.category.is_(None),
        )
        .order_by(Product.id)
        .all()
    )
    products = [p for p in products if not (p.suggested_source or "").startswith(SOURCE_PREFIX)]
    return products[:limit] if limit else products


def chunk(items, size):
    """Dzieli listę na części po size elementów."""
    return [items[i:i + size] for i in range(0, len(items), size)]


def _one_line(text):
    """Zamienia tekst na jedną linię bez znaków, które psują format listy."""
    return " ".join(str(text or "").replace("|", "/").split())


def build_batch_text(categories, products, number, total):
    """Buduje gotowy tekst jednej paczki do wklejenia w czacie z AI:
    polecenie, lista kategorii (numerowana), zasady i lista produktów."""
    lines = [PROMPT_INTRO, "", f"KATEGORIE (paczka {number} z {total}), wybieraj wyłącznie numer:"]
    for position, name in enumerate(categories, start=1):
        lines.append(f"{position}. {name}")
    lines += ["", PROMPT_RULES, "", "PRODUKTY (id | nazwa | podpowiedź producenta):"]
    for product in products:
        hint = _one_line(product.suggested_manufacturer) or "-"
        lines.append(f"{product.id} | {_one_line(product.name)} | {hint}")
    return "\n".join(lines) + "\n"


def parse_ai_answer(text, categories):
    """Czyta odpowiedź AI (wiersze id;producent;numer_kategorii;pewność).
    Pomija wiersze, które nie zaczynają się od liczby (komentarze, nagłówki, ogrodzenia ```).
    Zwraca (lista Suggestion, lista problemów jako par (powód, wiersz))."""
    suggestions = []
    problems = []

    for raw in text.splitlines():
        line = raw.strip().strip("`").strip()
        if not line or not line[0].isdigit():
            continue

        parts = [part.strip() for part in re.split(r"[;|\t]", line)]
        if len(parts) < 4 and ";" not in line and "|" not in line:
            parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            problems.append(("za mało pól", raw))
            continue

        id_text, manufacturer, category_text, confidence_text = parts[0], parts[1], parts[2], parts[3]

        if not id_text.isdigit():
            problems.append(("id nie jest liczbą", raw))
            continue

        if manufacturer in ("", "?", "-"):
            manufacturer = None

        category = None
        if category_text.isdigit() and 1 <= int(category_text) <= len(categories):
            category = categories[int(category_text) - 1]
        elif category_text not in ("", "?", "-", "0"):
            matches = [name for name in categories if name.lower() == category_text.lower()]
            if matches:
                category = matches[0]
            else:
                problems.append(("nieznana kategoria", raw))
                continue

        if manufacturer is None and category is None:
            problems.append(("brak producenta i kategorii", raw))
            continue

        confidence = CONFIDENCE_CODES.get(confidence_text.strip().upper()[:1], "low")
        suggestions.append(Suggestion(int(id_text), manufacturer, category, confidence))

    return suggestions, problems


def apply_suggestions(session, suggestions, apply=True):
    """Zapisuje podpowiedzi AI w produktach (jako podpowiedzi, nie jako zatwierdzone dane).
    Produktów już zatwierdzonych nie rusza. Pusty producent z AI nie kasuje podpowiedzi z WAPRO.
    apply=False tylko liczy, co by się stało. Zwraca ApplyResult."""
    result = ApplyResult()
    seen = set()

    for suggestion in suggestions:
        if suggestion.product_id in seen:
            result.duplicates += 1
        seen.add(suggestion.product_id)

        product = session.get(Product, suggestion.product_id)
        if product is None:
            result.unknown_id += 1
            continue
        if (
            product.review_status == "confirmed"
            and product.manufacturer is not None
            and product.category is not None
        ):
            result.already_confirmed += 1
            continue

        if suggestion.manufacturer is not None:
            product.suggested_manufacturer = suggestion.manufacturer
        if suggestion.category is not None:
            product.suggested_category = suggestion.category
        product.suggested_source = SOURCE_PREFIX + suggestion.confidence
        result.applied += 1

    if apply:
        session.commit()
    else:
        session.rollback()

    return result