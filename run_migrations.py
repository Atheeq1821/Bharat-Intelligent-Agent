"""
Opens the Supabase SQL editor and prints migration SQL to paste.
Run: python run_migrations.py
"""
import webbrowser, pathlib, sys

SUPABASE_PROJECT = "rhkxmlexcfjeyuklgzfo"
EDITOR_URL = f"https://supabase.com/dashboard/project/{SUPABASE_PROJECT}/sql/new"

BASE = pathlib.Path(__file__).parent / "migrations"

for f in sorted(BASE.glob("*.sql")):
    print(f"\n{'='*70}")
    print(f"  {f.name}")
    print('='*70)
    print(f.read_text())

print(f"\n{'='*70}")
print("  Opening Supabase SQL editor in your browser...")
print(f"  {EDITOR_URL}")
print("  Paste 001_schema.sql first, run it, then paste 002_seed_data.sql")
print('='*70)
webbrowser.open(EDITOR_URL)
