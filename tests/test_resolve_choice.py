from services.classification_service import resolve_choice


def test_number_picks_existing_option():
    assert resolve_choice("2", ["Atomicus", "Vortex"]) == "Vortex"


def test_text_is_a_new_name():
    assert resolve_choice("Swarovski", ["Atomicus", "Vortex"]) == "Swarovski"


def test_number_out_of_range_is_taken_as_name():
    assert resolve_choice("10", ["Atomicus", "Vortex"]) == "10"


def test_zero_is_taken_as_name():
    assert resolve_choice("0", ["Atomicus"]) == "0"


def test_empty_text_returns_none():
    assert resolve_choice("   ", ["Atomicus"]) is None


def test_number_with_empty_options_is_a_name():
    assert resolve_choice("1", []) == "1"


def test_text_is_trimmed():
    assert resolve_choice("  Sony ", []) == "Sony"