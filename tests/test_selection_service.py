from services.selection_service import parse_selection


def test_single_number():
    assert parse_selection("2", 5) == [1]


def test_numbers_separated_by_comma_and_space():
    assert parse_selection("1,3", 5) == [0, 2]
    assert parse_selection("1 3", 5) == [0, 2]
    assert parse_selection("1, 3 ,4", 5) == [0, 2, 3]


def test_range():
    assert parse_selection("2-4", 5) == [1, 2, 3]


def test_range_mixed_with_numbers():
    assert parse_selection("1,3-4", 5) == [0, 2, 3]


def test_duplicates_are_removed_keeping_first_occurrence():
    assert parse_selection("3,1,3,1-2", 5) == [2, 0, 1]


def test_order_given_by_user_is_kept():
    assert parse_selection("4,2", 5) == [3, 1]


def test_empty_text_is_invalid():
    assert parse_selection("", 5) is None
    assert parse_selection("   ", 5) is None


def test_number_out_of_range_is_invalid():
    assert parse_selection("0", 5) is None
    assert parse_selection("6", 5) is None
    assert parse_selection("1,6", 5) is None
    assert parse_selection("4-7", 5) is None


def test_reversed_range_is_invalid():
    assert parse_selection("4-2", 5) is None


def test_garbage_is_invalid():
    assert parse_selection("abc", 5) is None
    assert parse_selection("1,a", 5) is None
    assert parse_selection("1-", 5) is None
    assert parse_selection("-3", 5) is None
    assert parse_selection("1-2-3", 5) is None
    assert parse_selection("-1", 5) is None