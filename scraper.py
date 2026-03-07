import requests
import json
import os
import base64
from datetime import datetime

API_KEY  = '7eb0408f27764cd139b0c35cb9f85e45'
API_URL  = 'https://search.api.careerjet.net/v4/query'

# Basic Auth: Base64(apikey + ":")
credentials = base64.b64encode(f"{API_KEY}:".encode()).decode()

KEYWORDS  = 'Pflegefachkraft Pflege Krankenpflege'
LOCATION  = 'Schweiz'
PAGE_SIZE = 50
PAGES     = 4

def fetch_jobs():
    all_jobs = []
    seen_urls = set()

    headers = {
        'Authorization': f'Basic {credentials}',
        'User-Agent':    'Mozilla/5.0 (compatible; lebenplus-scraper/1.0)',
    }

    for page in range(1, PAGES + 1):
        params = {
            'locale_code': 'de_CH',
            'keywords':    KEYWORDS,
            'location':    LOCATION,
            'page_size':   PAGE_SIZE,
            'page':        page,
            'user_ip':     '1.1.1.1',
            'user_agent':  'Mozilla/5.0',
        }
        try:
            r = requests.get(API_URL, params=params, headers=headers, timeout=30)
            print(f"HTTP Status: {r.status_code}")
            print(f"Antwort: {r.text[:500]}")

            data = r.json()

            if data.get('type') != 'JOBS':
                print(f"Seite {page}: type={data.get('type')} message={data.get('message')}")
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

            print(f"Seite {page}: {len(jobs)} Jobs (total: {len(all_jobs)})")

            if len(jobs) < PAGE_SIZE:
                break

        except Exception as e:
            print(f"Fehler auf Seite {page}: {e}")
            break

    return all_jobs

def main():
    print(f"Starte Scraper – {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    jobs = fetch_jobs()
    print(f"Gesamt: {len(jobs)} Jobs gefunden")

    output = {
        'updated': datetime.now().strftime('%d.%m.%Y %H:%M'),
        'total':   len(jobs),
        'jobs':    jobs,
    }

    os.makedirs('data', exist_ok=True)
    with open('data/jobs.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Gespeichert in data/jobs.json ✅")

if __name__ == '__main__':
    main()
