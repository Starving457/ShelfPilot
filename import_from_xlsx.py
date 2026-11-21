import os
import sys

from database.db import SessionLocal
from services.classification_service import list_products_to_fill
from services.import_service import import_articles
from services.xlsx_reader import read_articles_from_xlsx, XLSX_KINDS


def print_summary(summary):
    print(f"  nowe produkty:             {summary.created}")
    print(f"  zaktualizowane:            {summary.updated}")
    print(f"  bez zmian:                 {summary.unchanged}")
    print(f"  nieobecne w pliku:         {summary.missing} (produkt zostaje, stan nieznany)")
    print(f"  pominięte (konflikt kodu): {len(summary.conflicts)}")

    if summary.new_products:
        print("\nNowe produkty (pierwsze 10):")
        for name in summary.new_products[:10]:
            print(f"  - {name}")
    if summary.conflicts:
        print("\nKody, które zajmuje już inny produkt:")
        for code in summary.conflicts[:10]:
            print(f"  - {code}")


# Ścieżkę do pliku można podać jako argument albo wpisać po uruchomieniu
if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = input("Ścieżka do pliku .xlsx z eksportu WAPRO: ")
path = path.strip().strip('"').strip("'")

if not os.path.isfile(path):
    print(f"Nie znaleziono pliku: {path}")
    raise SystemExit(1)

try:
    result = read_articles_from_xlsx(path)
except ValueError as error:
    print(f"Nie mogę odczytać pliku: {error}")
    raise SystemExit(1)

print(f"Rodzaje artykułów: {', '.join(XLSX_KINDS)}")
print(f"Wczytano z pliku: {len(result.articles)} artykułów")
print(f"  pominięto inne rodzaje (np. usługi): {result.skipped_other_kind}")
print(f"  pominięto bez indeksu katalogowego:  {result.skipped_no_code}")
print(f"  pominięto bez poprawnego numeru:     {result.skipped_bad_id}")

session = SessionLocal()

preview = import_articles(session, result.articles, apply=False)
if preview.status == "empty_source":
    print("W pliku nie ma żadnych artykułów do importu, nic nie zmieniam.")
    session.close()
    raise SystemExit(1)

print("\nPo imporcie zmieni się:")
print_summary(preview)

if preview.created + preview.updated + preview.missing == 0:
    print("\nBrak zmian do zapisania.")
else:
    answer = input("\nZastosować zmiany? (T/N): ").strip().upper()
    if answer == "T":
        import_articles(session, result.articles)
        print("Zapisano.")
        to_fill = len(list_products_to_fill(session))
        if to_fill:
            print(f"\n{to_fill} produktów (stan > 0) czeka na producenta i kategorię.")
            print("Uzupełnisz je skryptem fill_attributes.py.")
    else:
        print("Anulowano, nic nie zapisano.")

session.close()