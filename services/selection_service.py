def parse_selection(text, count):
    """Zamienia tekst typu "1,3" lub "2-4 6" na listę indeksów (od 0).

    Zwraca None, gdy tekst jest pusty albo nieprawidłowy (zły format,
    numer spoza zakresu 1..count, odwrócony zakres). Powtórzenia są pomijane,
    kolejność pierwszego wystąpienia zostaje zachowana.
    """
    parts = text.replace(",", " ").split()
    if not parts:
        return None

    indices = []
    for part in parts:
        if part.isdigit():
            start = end = int(part)
        elif part.count("-") == 1:
            left, right = part.split("-")
            if not (left.isdigit() and right.isdigit()):
                return None
            start, end = int(left), int(right)
        else:
            return None

        if start < 1 or end > count or start > end:
            return None

        for number in range(start, end + 1):
            if number - 1 not in indices:
                indices.append(number - 1)

    return indices