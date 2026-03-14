import requests
import json
import os
import time
from datetime import datetime
import google.generativeai as genai

BACKEND_URL = 'https://lebenplus-backend.onrender.com/api/jobs'
PAGE_SIZE   = 20
PAGES       = 10
MAX_JOBS    = 10

KATEGORIEN = [
    { 'name': 'pflege', 'keywords': 'Pflege',          'location': 'Schweiz', 'output': 'data/pflege-jobs.json', 'max_jobs': 10  },
    { 'name': 'sap',    'keywords': 'SAP',              'location': 'Schweiz', 'output': 'data/sap-jobs.json',    'max_jobs': 10  },
    { 'name': 'alle',   'keywords': 'Stellen Schweiz',  'location': 'Schweiz', 'output': 'data/alle-jobs.json',   'max_jobs': 200 },
]

# Begriffe die im Titel vorkommen → Job wird aus alle-jobs.json herausgefiltert
EXCLUDE_TERMS = [
    'pflege', 'pflegefach', 'arzt', 'ärztin', 'arztpraxis', 'apotheker', 'apotheke',
    'sap', 'ingenieur', 'maschinenbau', 'automatisierung', 'elektro', 'elektriker',
    'software', 'entwickler', 'it-', 'informatik', 'cybersecurity',
]


def filter_jobs(jobs):
    """Filtert Jobs heraus deren Titel einen der EXCLUDE_TERMS enthält."""
    def is_excluded(job):
        title = (job.get('title') or '').lower()
        return any(term in title for term in EXCLUDE_TERMS)
    return [j for j in jobs if not is_excluded(j)]


def fetch_jobs(keywords, location, max_jobs=MAX_JOBS):
    all_jobs  = []
    seen_urls = set()

    for page in range(1, PAGES + 1):
        if len(all_jobs) >= max_jobs:
            break

        params = { 'keywords': keywords, 'location': location, 'pagesize': PAGE_SIZE, 'page': page }
        try:
            r = requests.get(BACKEND_URL, params=params, timeout=60)
            print(f"  Seite {page} – HTTP {r.status_code}")
            data = r.json()

            if data.get('type') != 'JOBS':
                print(f"  Seite {page}: type={data.get('type')}")
                break

            jobs = data.get('jobs', [])
            if not jobs:
                break

            for job in jobs:
                if len(all_jobs) >= max_jobs:
                    break

                url = job.get('url', '')
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                all_jobs.append({
                    'id':          job.get('id', ''),
                    'title':       job.get('title', ''),
                    'company':     job.get('company', ''),
                    'locations':   job.get('locations', ''),
                    'date':        job.get('date', ''),
                    'salary':      job.get('salary', ''),
                    'description': job.get('description', ''),
                    'url':         url,
                })

            print(f"  Seite {page}: {len(jobs)} Jobs (total: {len(all_jobs)})")

        except Exception as e:
            print(f"  Fehler auf Seite {page}: {e}")
            break

    return all_jobs


def needs_improvement(desc):
    """True wenn Beschreibung kurz oder abgeschnitten wirkt."""
    if not desc:
        return False
    text = desc.strip()
    if len(text) < 300:
        return True
    if text.endswith('...') or text.endswith('…'):
        return True
    if text and text[-1] not in '.!?»"\'':
        return True
    return False


def improve_descriptions(gemini_model, output_files):
    """Zweiter Durchlauf: kurze/abgeschnittene Beschreibungen via Gemini verbessern."""
    print("\n=== ZWEITER DURCHLAUF: Beschreibungen verbessern ===")

    for filepath in output_files:
        print(f"\n  Verarbeite {filepath} ...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  Fehler beim Laden: {e}")
            continue

        jobs = data.get('jobs', [])
        improved = 0

        for job in jobs:
            desc = job.get('description', '')
            if not needs_improvement(desc):
                continue

            print(f"    Verbessere: {job.get('title', '')} @ {job.get('company', '')}")
            prompt = f"""Du erhältst einen Ausschnitt einer Stellenbeschreibung für die Stelle "{job['title']}" bei "{job['company']}".
Aufgabe:
1. Entferne alle Telefonnummern, E-Mail-Adressen und URLs
2. Schreibe abgeschnittene Sätze logisch zu Ende - nur basierend auf dem Kontext
3. Strukturiere mit Abschnitten: Über die Stelle / Ihre Aufgaben / Ihr Profil / Wir bieten - aber NUR wenn diese Info im Text vorhanden ist
4. Erfinde KEINE neuen Details die nicht im Text stehen
5. Behalte alle originalen Formulierungen so nah wie möglich
6. Gib nur den aufbereiteten Text zurück, kein Markdown, keine Erklärungen

Originaltext:
{desc}"""

            for attempt in range(3):
                try:
                    response = gemini_model.generate_content(prompt)
                    job['description'] = response.text.strip()
                    improved += 1
                    break
                except Exception as e:
                    if '429' in str(e):
                        wait = 30 * (attempt + 1)
                        print(f"    Rate limit – warte {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"    Fehler: {e}")
                        break

            time.sleep(2)

        data['jobs'] = jobs
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  {improved} Beschreibungen verbessert → {filepath}")


def main():
    print(f"Starte Scraper – {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    os.makedirs('data', exist_ok=True)

    all_combined = []
    now_str = datetime.now().strftime('%d.%m.%Y %H:%M')
    output_files = []

    for kat in KATEGORIEN:
        print(f"\n=== {kat['name'].upper()} ===")
        jobs = fetch_jobs(kat['keywords'], kat['location'], kat.get('max_jobs', MAX_JOBS))

        # Für die 'alle' Kategorie: Spezifische Berufe herausfiltern
        if kat['name'] == 'alle':
            before = len(jobs)
            jobs = filter_jobs(jobs)
            print(f"  Filter: {before} → {len(jobs)} Jobs ({before - len(jobs)} herausgefiltert)")

        print(f"\nGesamt: {len(jobs)} Jobs")
        output = {
            'updated': now_str,
            'total':   len(jobs),
            'jobs':    jobs,
        }
        with open(kat['output'], 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Gespeichert: {kat['output']}")
        output_files.append(kat['output'])

        if kat['name'] != 'alle':
            all_combined.extend(jobs)

    # Kombinierte jobs.json für das Frontend (ohne alle-jobs)
    combined_path = 'data/jobs.json'
    combined = {
        'updated': now_str,
        'total':   len(all_combined),
        'jobs':    all_combined,
    }
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\nKombinierte Datei gespeichert: {combined_path} ({len(all_combined)} Jobs)")
    output_files.append(combined_path)

    # Zweiter Durchlauf: Gemini verbessert kurze/abgeschnittene Beschreibungen
    api_key = os.environ.get('GEMINI_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        improve_descriptions(model, output_files)
    else:
        print("\nGEMINI_API_KEY nicht gesetzt – zweiter Durchlauf übersprungen.")


if __name__ == '__main__':
    main()
