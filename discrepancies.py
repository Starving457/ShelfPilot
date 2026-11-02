from datetime import date

from database.db import SessionLocal
from services.inventory_service import get_day_report


def ask_date():
    """Pyta o dzień (Enter = dziś, albo RRRR-MM-DD). Pyta do skutku."""
    while True:
        text = input("Dzień raportu (Enter = dziś, albo RRRR-MM-DD): ").strip()

        if text == "":
            return date.today()

        try:
            return date.fromisoformat(text)
        except ValueError:
            print("Nieprawidłowa data. Przykład: 2026-11-02")


def format_quantity(value):
    return "?" if value is None else str(value)


def print_report(report, group_label):
    print(f"\nRaport za {report.day}{group_label}")

    if report.counted_products == 0:
        print("Tego dnia nic nie policzono.")
        return

    print(f"Policzono produktów: {report.counted_products}")
    print(f"  zgodnych ze stanem WAPRO: {report.matching}")
    print(f"  z niedoborem: {report.shortages}")
    print(f"  z nadwyżką: {report.surpluses}")
    if report.unknown_wapro > 0:
        print(f"  bez znanego stanu WAPRO: {report.unknown_wapro}")
    net = "0" if report.net_difference == 0 else f"{report.net_difference:+d}"
    print(f"Suma różnic: {net} szt.")

    if report.coverage:
        print("\nPokrycie grup:")
        for number, item in enumerate(report.coverage, start=1):
            print(f"{number}. {item.manufacturer} / {item.category}: policzono {item.counted} z {item.total}")

    if not report.lines:
        print("\nBrak rozbieżności.")
        return

    print("\nRozbieżności (od największej):")
    for line in report.lines:
        if line.difference is None:
            difference = "brak stanu WAPRO"
        else:
            difference = f"różnica: {line.difference:+d}"
        note = "  [znaleziony, WAPRO miał 0]" if line.is_extra else ""
        print(
            f"  {line.product.code} | {line.product.name} | "
            f"WAPRO: {format_quantity(line.wapro_quantity)} | policzono: {line.counted_quantity} | {difference}{note}"
        )


session = SessionLocal()

day = ask_date()
manufacturer = None
category = None

while True:
    report = get_day_report(session, day, manufacturer, category)

    label = f" ({manufacturer} / {category})" if manufacturer is not None else ""
    print_report(report, label)

    if not report.coverage and manufacturer is None:
        break

    answer = input("\nNumer grupy, by zawęzić / [W]szystko / Enter = koniec: ").strip().upper()

    if answer == "":
        break
    elif answer == "W":
        manufacturer = None
        category = None
    elif answer.isdigit() and manufacturer is None and 1 <= int(answer) <= len(report.coverage):
        chosen = report.coverage[int(answer) - 1]
        manufacturer = chosen.manufacturer
        category = chosen.category
    else:
        print("Nieznana opcja.")

session.close()