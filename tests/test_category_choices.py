from services.classification_service import (
    filter_options,
    find_similar,
    load_seed_categories,
    merge_options,
)


def test_load_seed_categories_skips_comments_and_blank_lines(tmp_path):
    path = tmp_path / "categories.txt"
    path.write_text("# comment\n\nLornetki\n  Lunety  \n# another\nAparaty\n", encoding="utf-8")

    assert load_seed_categories(path) == ["Lornetki", "Lunety", "Aparaty"]


def test_load_seed_categories_handles_bom_from_notepad(tmp_path):
    path = tmp_path / "categories.txt"
    path.write_bytes("\ufeffLornetki\nAparaty\n".encode("utf-8"))

    assert load_seed_categories(path) == ["Lornetki", "Aparaty"]


def test_load_seed_categories_missing_file_gives_empty_list(tmp_path):
    assert load_seed_categories(tmp_path / "nope.txt") == []


def test_merge_options_removes_duplicates_ignoring_case():
    assert merge_options(["Lornetki", "Aparaty"], ["lornetki", "Filtry"]) == ["Aparaty", "Filtry", "Lornetki"]


def test_merge_options_keeps_spelling_from_first_list():
    assert merge_options(["Lornetki"], ["LORNETKI"]) == ["Lornetki"]


def test_merge_options_sorts_ignoring_case():
    assert merge_options(["zeiss", "Atomicus"]) == ["Atomicus", "zeiss"]


def test_filter_options_matches_all_words_in_any_order():
    options = ["Lunety celownicze", "Lunety obserwacyjne", "Lornetki"]

    assert filter_options(options, "celown lunet") == ["Lunety celownicze"]


def test_filter_options_ignores_case():
    assert filter_options(["Lornetki"], "LORN") == ["Lornetki"]


def test_filter_options_empty_text_returns_everything():
    assert filter_options(["A", "B"], "  ") == ["A", "B"]


def test_find_similar_catches_typo():
    assert find_similar("Lornetkii", ["Lornetki", "Aparaty"]) == ["Lornetki"]


def test_find_similar_catches_other_case():
    assert find_similar("lornetki", ["Lornetki"]) == ["Lornetki"]


def test_find_similar_catches_singular_form():
    assert find_similar("Lornetka", ["Lornetki"]) == ["Lornetki"]


def test_find_similar_ignores_different_names():
    assert find_similar("Aparaty", ["Lornetki", "Filtry", "Latarki"]) == []


def test_find_similar_puts_closest_first():
    assert find_similar("Filtr", ["Filtry", "Filtr ND"])[0] == "Filtry"