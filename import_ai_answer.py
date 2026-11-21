import os
import sys

from database.db import SessionLocal
from services.ai_service import apply_suggestions, parse_ai_answer
from services.classification_service import load_seed_categories

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_FILE = os.path.join(BASE_DIR, "data", "categories.txt")
CATEGORIES_USED_FILE = os.path.join(BASE_DIR, "export", "kategorie_uzyte.txt")

# Ścieżkę do pliku z odpowiedzią AI można podać jako argument albo wpisać po uruchomieniu
if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = input("Ścieżka do pliku z odpowiedzią AI: ")
path = path.strip().strip('"').strip("'")

if not os.path.isfile(path):
    print(f"Nie znaleziono pliku: {path}")
    raise SystemExit(1)

# Numery kategorii w odpowiedzi dotyczą listy z chwili eksportu (kopia zapisana przez export_for_ai.py)
categories_file = CATEGORIES_USED_FILE if os.path.isfile(CATEGORIES_USED_FILE) else CATEGORIES_FILE
categories = load_seed_categories(categories_file)
if not categories:
    print("Brak listy kategorii, nie da się odczytać numerów kategorii.")
    raise SystemExit(1)

with open(path, encoding="utf-8-sig", errors="replace") as file:
    text = file.read()

suggestions, problems = parse_ai_answer(text, categories)
print(f"Odczytano wierszy z podpowiedziami: {len(suggestions)}")
print(f"Wiersze z problemem (pominięte):    {len(problems)}")
for reason, line in problems[:10]:
    print(f"  - {reason}: {line}")
if len(problems) > 10:
    print(f"  ... i {len(problems) - 10} kolejnych")

if not suggestions:
    print("Nie ma nic do zapisania.")
    raise SystemExit(1)

session = SessionLocal()
preview = apply_suggestions(session, suggestions, apply=False)

print("\nPo wczytaniu:")
print(f"  zapisane podpowiedzi:             {preview.applied}")
print(f"  nieznane id produktu (pominięte): {preview.unknown_id}")
print(f"  już zatwierdzone (pominięte):     {preview.already_confirmed}")
print(f"  powtórzone id:                    {preview.duplicates}")

if preview.applied == 0:
    print("\nNic do zapisania.")
else:
    answer = input("\nZapisać podpowiedzi? (T/N): ").strip().upper()
    if answer == "T":
        apply_suggestions(session, suggestions)
        print("Zapisano. Teraz możesz je zatwierdzić: python approve_ai.py")
    else:
        print("Anulowano, nic nie zapisano.")

session.close()