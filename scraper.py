import requests
import json
import os
from datetime import datetime

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


def main():
    print(f"Starte Scraper – {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    os.makedirs('data', exist_ok=True)

    all_combined = []
    now_str = datetime.now().strftime('%d.%m.%Y %H:%M')

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

        if kat['name'] != 'alle':
            all_combined.extend(jobs)

    # Kombinierte jobs.json für das Frontend (ohne alle-jobs)
    combined = {
        'updated': now_str,
        'total':   len(all_combined),
        'jobs':    all_combined,
    }
    with open('data/jobs.json', 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\nKombinierte Datei gespeichert: data/jobs.json ({len(all_combined)} Jobs)")


if __name__ == '__main__':
    main()
