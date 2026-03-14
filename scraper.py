import requests
import json
import os
from datetime import datetime

BACKEND_URL = 'https://lebenplus-backend.onrender.com/api/jobs'
PAGE_SIZE   = 20
PAGES       = 20

KATEGORIEN = [
    {
        'name': 'pflege',
        'keywords': ['Pflege', 'Pflegefachperson', 'Pflegefachmann', 'Pflegefachfrau',
                     'Krankenpflege', 'Spitex', 'FaGe', 'Betagtenpflege', 'Heimleitung'],
        'location': 'Schweiz',
        'output': 'data/pflege-jobs.json',
        'max_jobs': 200,
    },
    {
        'name': 'sap',
        'keywords': ['SAP', 'ABAP', 'Fiori', 'S4HANA', 'IT', 'Software',
                     'Informatik', 'Entwickler', 'DevOps', 'Cloud', 'Cybersecurity', 'Data'],
        'location': 'Schweiz',
        'output': 'data/sap-jobs.json',
        'max_jobs': 200,
    },
    {
        'name': 'alle',
        'keywords': ['Stellen Schweiz'],
        'location': 'Schweiz',
        'output': 'data/alle-jobs.json',
        'max_jobs': 200,
    },
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


def set_standard_description(job):
    """Setzt eine personalisierte Standardbeschreibung für jeden Job."""
    title    = job.get('title', 'diese Stelle')
    company  = job.get('company', 'diesem Unternehmen')
    location = job.get('locations', 'der Schweiz')
    job['description'] = (
        f"Wir haben eine spannende Stelle als {title} bei {company} in {location} für Sie. "
        f"Senden Sie uns eine kurze Anfrage und wir melden uns umgehend mit allen Details "
        f"zu dieser Position bei Ihnen."
    )


def fetch_jobs_for_keyword(keyword, location, max_jobs, seen_urls):
    """Holt Jobs für ein einzelnes Keyword über mehrere Seiten."""
    collected = []

    for page in range(1, PAGES + 1):
        if len(collected) >= max_jobs:
            break

        params = {'keywords': keyword, 'location': location, 'pagesize': PAGE_SIZE, 'page': page}
        try:
            r = requests.get(BACKEND_URL, params=params, timeout=60)
            print(f"  [{keyword}] Seite {page} – HTTP {r.status_code}")
            data = r.json()

            if data.get('type') != 'JOBS':
                print(f"  [{keyword}] Seite {page}: type={data.get('type')}")
                break

            jobs = data.get('jobs', [])
            if not jobs:
                break

            for job in jobs:
                if len(collected) >= max_jobs:
                    break
                url = job.get('url', '')
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                entry = {
                    'id':        job.get('id', ''),
                    'title':     job.get('title', ''),
                    'company':   job.get('company', ''),
                    'locations': job.get('locations', ''),
                    'date':      job.get('date', ''),
                    'salary':    job.get('salary', ''),
                    'url':       url,
                }
                set_standard_description(entry)
                collected.append(entry)

            print(f"  [{keyword}] Seite {page}: {len(jobs)} Jobs (gesammelt: {len(collected)})")

        except Exception as e:
            print(f"  [{keyword}] Fehler auf Seite {page}: {e}")
            break

    return collected


def fetch_jobs(keywords, location, max_jobs=200):
    """Holt Jobs für eine Liste von Keywords (dedupliziert nach URL)."""
    all_jobs = []
    seen_urls = set()

    for keyword in keywords:
        if len(all_jobs) >= max_jobs:
            break
        jobs = fetch_jobs_for_keyword(keyword, location, max_jobs - len(all_jobs), seen_urls)
        all_jobs.extend(jobs)
        print(f"  → '{keyword}': {len(jobs)} neue Jobs (gesamt: {len(all_jobs)})")

    return all_jobs


def main():
    print(f"Starte Scraper – {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    os.makedirs('data', exist_ok=True)

    all_combined = []
    now_str = datetime.now().strftime('%d.%m.%Y %H:%M')
    output_files = []

    for kat in KATEGORIEN:
        print(f"\n=== {kat['name'].upper()} ===")
        jobs = fetch_jobs(kat['keywords'], kat['location'], kat.get('max_jobs', 200))

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

    combined_path = 'data/jobs.json'
    combined = {
        'updated': now_str,
        'total':   len(all_combined),
        'jobs':    all_combined,
    }
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\nKombinierte Datei gespeichert: {combined_path} ({len(all_combined)} Jobs)")


if __name__ == '__main__':
    main()
