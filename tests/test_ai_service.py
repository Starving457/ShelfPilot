from database.models import Product
from services.ai_service import (
    Suggestion,
    apply_suggestions,
    build_batch_text,
    chunk,
    parse_ai_answer,
    select_products_for_export,
)

CATEGORIES = ["Lornetki", "Lunety celownicze", "Inne"]


def _product(session, code, name="Product", quantity=3, **fields):
    product = Product(code=code, name=name, wapro_quantity=quantity, **fields)
    session.add(product)
    session.commit()
    return product


# --- select_products_for_export ---


def test_export_selects_only_products_with_stock(session):
    _product(session, "A", quantity=3)
    _product(session, "B", quantity=0)
    _product(session, "C", quantity=None)

    assert [p.code for p in select_products_for_export(session)] == ["A"]


def test_export_skips_confirmed_products(session):
    _product(session, "A")
    _product(session, "B", manufacturer="Vortex", category="Lornetki", review_status="confirmed")

    assert [p.code for p in select_products_for_export(session)] == ["A"]


def test_export_skips_products_that_already_have_ai_suggestion(session):
    _product(session, "A")
    _product(session, "B", suggested_source="ai-high")
    _product(session, "C", suggested_source="wapro")

    assert [p.code for p in select_products_for_export(session)] == ["A", "C"]


def test_export_respects_limit(session):
    for code in "ABCDE":
        _product(session, code)

    assert len(select_products_for_export(session, limit=2)) == 2


def test_chunk_splits_list():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_empty_list():
    assert chunk([], 3) == []


# --- build_batch_text ---


def test_batch_text_contains_numbered_categories_and_products(session):
    product = _product(session, "A", name="VORTEX DIAMONDBACK HD 10X42", suggested_manufacturer="Vortex")

    text = build_batch_text(CATEGORIES, [product], 1, 3)

    assert "1. Lornetki" in text
    assert "3. Inne" in text
    assert f"{product.id} | VORTEX DIAMONDBACK HD 10X42 | Vortex" in text
    assert "paczka 1 z 3" in text


def test_batch_text_uses_dash_when_no_hint(session):
    product = _product(session, "A", name="Narty")

    assert f"{product.id} | Narty | -" in build_batch_text(CATEGORIES, [product], 1, 1)


def test_batch_text_removes_pipes_and_newlines_from_names(session):
    product = _product(session, "A", name="Narty | LUX\nPRO")

    assert f"{product.id} | Narty / LUX PRO | -" in build_batch_text(CATEGORIES, [product], 1, 1)


# --- parse_ai_answer ---


def test_parse_basic_line():
    suggestions, problems = parse_ai_answer("12;Vortex;1;W", CATEGORIES)

    assert suggestions == [Suggestion(12, "Vortex", "Lornetki", "high")]
    assert problems == []


def test_parse_confidence_levels():
    suggestions, _ = parse_ai_answer("1;A;1;W\n2;B;1;S\n3;C;1;N", CATEGORIES)

    assert [s.confidence for s in suggestions] == ["high", "medium", "low"]


def test_parse_unknown_confidence_counts_as_low():
    suggestions, _ = parse_ai_answer("1;A;1;X\n2;B;1;", CATEGORIES)

    assert [s.confidence for s in suggestions] == ["low", "low"]


def test_parse_ignores_noise_lines_and_code_fences():
    text = "Oto wyniki:\n```\nid;producent;kategoria;pewność\n12;Vortex;1;W\n```\nGotowe."

    suggestions, problems = parse_ai_answer(text, CATEGORIES)

    assert [s.product_id for s in suggestions] == [12]
    assert problems == []


def test_parse_accepts_pipes_and_tabs_and_spaces_around():
    suggestions, _ = parse_ai_answer("1 | Vortex | 2 | S\n2\tSony\t3\tW", CATEGORIES)

    assert [(s.manufacturer, s.category) for s in suggestions] == [("Vortex", "Lunety celownicze"), ("Sony", "Inne")]


def test_parse_accepts_commas_when_no_semicolons():
    suggestions, _ = parse_ai_answer("1,Vortex,1,W", CATEGORIES)

    assert suggestions == [Suggestion(1, "Vortex", "Lornetki", "high")]


def test_parse_accepts_category_name_instead_of_number():
    suggestions, _ = parse_ai_answer("1;Vortex;lornetki;W", CATEGORIES)

    assert suggestions[0].category == "Lornetki"


def test_parse_unknown_manufacturer_becomes_none():
    suggestions, _ = parse_ai_answer("1;?;1;N", CATEGORIES)

    assert suggestions[0].manufacturer is None
    assert suggestions[0].category == "Lornetki"


def test_parse_unknown_category_number_is_a_problem():
    suggestions, problems = parse_ai_answer("1;Vortex;99;W\n2;Vortex;Abc;W", CATEGORIES)

    assert suggestions == []
    assert [reason for reason, _ in problems] == ["nieznana kategoria", "nieznana kategoria"]


def test_parse_question_mark_category_is_allowed_when_manufacturer_known():
    suggestions, problems = parse_ai_answer("1;Vortex;?;N", CATEGORIES)

    assert suggestions[0].category is None
    assert problems == []


def test_parse_row_without_manufacturer_and_category_is_a_problem():
    suggestions, problems = parse_ai_answer("1;?;?;N", CATEGORIES)

    assert suggestions == []
    assert problems[0][0] == "brak producenta i kategorii"


def test_parse_too_few_fields_is_a_problem():
    suggestions, problems = parse_ai_answer("1;Vortex", CATEGORIES)

    assert suggestions == []
    assert problems[0][0] == "za mało pól"


# --- apply_suggestions ---


def test_apply_stores_suggestions_with_confidence(session):
    product = _product(session, "A")

    result = apply_suggestions(session, [Suggestion(product.id, "Vortex", "Lornetki", "medium")])

    assert result.applied == 1
    assert product.suggested_manufacturer == "Vortex"
    assert product.suggested_category == "Lornetki"
    assert product.suggested_source == "ai-medium"
    assert product.review_status == "pending"
    assert product.manufacturer is None


def test_apply_does_not_touch_confirmed_products(session):
    product = _product(session, "A", manufacturer="Zeiss", category="Lunety", review_status="confirmed")

    result = apply_suggestions(session, [Suggestion(product.id, "Vortex", "Lornetki", "high")])

    assert result.already_confirmed == 1
    assert result.applied == 0
    assert product.suggested_manufacturer is None


def test_apply_counts_unknown_ids(session):
    result = apply_suggestions(session, [Suggestion(9999, "Vortex", "Lornetki", "high")])

    assert result.unknown_id == 1
    assert result.applied == 0


def test_apply_counts_duplicate_ids_and_last_row_wins(session):
    product = _product(session, "A")

    result = apply_suggestions(
        session,
        [Suggestion(product.id, "Vortex", "Lornetki", "low"), Suggestion(product.id, "Sony", "Inne", "high")],
    )

    assert result.duplicates == 1
    assert product.suggested_manufacturer == "Sony"
    assert product.suggested_source == "ai-high"


def test_apply_empty_manufacturer_keeps_wapro_hint(session):
    product = _product(session, "A", suggested_manufacturer="NIKON EUROPE B.V", suggested_source="wapro")

    apply_suggestions(session, [Suggestion(product.id, None, "Aparaty i kamery", "medium")])

    assert product.suggested_manufacturer == "NIKON EUROPE B.V"
    assert product.suggested_category == "Aparaty i kamery"


def test_apply_preview_changes_nothing(session):
    product = _product(session, "A")

    result = apply_suggestions(session, [Suggestion(product.id, "Vortex", "Lornetki", "high")], apply=False)

    assert result.applied == 1
    session.refresh(product)
    assert product.suggested_manufacturer is None