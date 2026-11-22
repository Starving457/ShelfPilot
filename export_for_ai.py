import glob
import os
import sys

from database.db import SessionLocal
from services.ai_service import build_batch_text, chunk, select_products_for_export
from services.classification_service import load_seed_categories

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_FILE = os.path.join(BASE_DIR, "data", "categories.txt")
EXPORT_DIR = os.path.join(BASE_DIR, "export")
CATEGORIES_USED_FILE = os.path.join(EXPORT_DIR, "kategorie_uzyte.txt")
DEFAULT_BATCH_SIZE = 400

# Użycie:
#   python export_for_ai.py            wszystkie produkty do sklasyfikowania, paczki po 400
#   python export_for_ai.py 30         tylko pierwsze 30 produktów (próba)
#   python export_for_ai.py 1000 250   pierwsze 1000 produktów, paczki po 250
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_BATCH_SIZE

categories = load_seed_categories(CATEGORIES_FILE)
if not categories:
    print(f"Nie znaleziono kategorii w pliku: {CATEGORIES_FILE}")
    raise SystemExit(1)

session = SessionLocal()
products = select_products_for_export(session, limit)
session.close()

if not products:
    print("Nie ma produktów do wysłania (wszystkie mają już producenta i kategorię albo podpowiedź AI).")
    raise SystemExit(0)

os.makedirs(EXPORT_DIR, exist_ok=True)
for old_file in glob.glob(os.path.join(EXPORT_DIR, "ai_paczka_*.txt")):
    os.remove(old_file)

batches = chunk(products, batch_size)
paths = []
for number, batch in enumerate(batches, start=1):
    path = os.path.join(EXPORT_DIR, f"ai_paczka_{number:02d}.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(build_batch_text(categories, batch, number, len(batches)))
    paths.append(path)

# Numery kategorii w odpowiedzi AI dotyczą listy z chwili eksportu, więc zapisujemy jej kopię
with open(CATEGORIES_USED_FILE, "w", encoding="utf-8", newline="\n") as file:
    file.write("\n".join(categories) + "\n")

print(f"Produktów do sklasyfikowania: {len(products)}")
print(f"Zapisano {len(batches)} paczek w folderze: {EXPORT_DIR}")

# Pierwszą paczkę otwieramy od razu w domyślnym programie (na Windowsie w Notatniku).
# Pozostałe paczki otwierasz sam, gdy będziesz gotowy na kolejną.
if hasattr(os, "startfile"):
    os.startfile(paths[0])
    print("Otworzyłem pierwszą paczkę. Zaznacz wszystko (Ctrl+A), skopiuj (Ctrl+C) i wklej do czatu z AI.")
else:
    print(f"Otwórz pierwszą paczkę: {paths[0]}")

print("\nCo dalej:")
print("1. Skopiuj całą zawartość paczki i wklej do czatu z AI.")
print("2. Odpowiedź AI zapisz do pliku, np. export/odpowiedz_01.txt (kodowanie UTF-8).")
print("3. Wczytaj ją poleceniem: python import_ai_answer.py export/odpowiedz_01.txt")
print("4. Zatwierdź propozycje poleceniem: python approve_ai.py")
if len(paths) > 1:
    print(f"5. Pozostałe paczki ({len(paths) - 1}) są w tym samym folderze: kolejne ai_paczka_NN.txt.")