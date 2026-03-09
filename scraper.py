import requests
import json
import os
from datetime import datetime

BACKEND_URL = 'https://lebenplus-backend.onrender.com/api/jobs'
PAGE_SIZE   = 20
PAGES       = 10

KATEGORIEN = [
    { 'name': 'pflege', 'keywords': 'Pflege', 'location': 'Schweiz', 'output': 'data/pflege-jobs.json' },
    { 'name': 'sap',    'keywords': 'SAP',    'location': 'Schweiz', 'output': 'data/sap-jobs.json' },
]

def fetch_jobs(keywords, location):
    all_jobs  = []
    seen_urls = set()

    for page in range(1, PAGES + 1):
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

    for kat in KATEGORIEN:
        print(f"\n=== {kat['name'].upper()} ===")
        jobs = fetch_jobs(kat['keywords'], kat['location'])
        print(f"\nGesamt: {len(jobs)} Jobs")
        output = {
            'updated': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'total':   len(jobs),
            'jobs':    jobs,
        }
        with open(kat['output'], 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Gespeichert: {kat['output']}")

if __name__ == '__main__':
    main()
