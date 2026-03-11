import requests
import json
import os
from datetime import datetime
import anthropic

BACKEND_URL = 'https://lebenplus-backend.onrender.com/api/jobs'
PAGE_SIZE   = 20
PAGES       = 10

KATEGORIEN = [
    { 'name': 'pflege', 'keywords': 'Pflege', 'location': 'Schweiz', 'output': 'data/pflege-jobs.json' },
    { 'name': 'sap',    'keywords': 'SAP',    'location': 'Schweiz', 'output': 'data/sap-jobs.json' },
]

ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'

PROMPT_TEMPLATE = (
    'Du erhältst einen kurzen Ausschnitt einer Stellenbeschreibung. '
    'Erstelle daraus eine strukturierte, professionelle Stellenbeschreibung auf Deutsch '
    'mit den Abschnitten: Über die Stelle, Ihre Aufgaben, Ihr Profil, Wir bieten. '
    'Erfinde keine spezifischen Details die nicht im Text stehen, aber fülle sinnvoll aus '
    'basierend auf der Jobbezeichnung und dem Unternehmen. '
    'Entferne alle Telefonnummern, E-Mail-Adressen und URLs. '
    'Gib nur den formatierten Text zurück ohne Markdown-Symbole.'
)

_anthropic_client = anthropic.Anthropic()


def enrich_description(title: str, company: str, raw_description: str) -> str:
    user_message = (
        f'Jobtitel: {title}\n'
        f'Unternehmen: {company}\n\n'
        f'Kurze Stellenbeschreibung:\n{raw_description}'
    )
    try:
        message = _anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[
                {
                    'role': 'user',
                    'content': f'{PROMPT_TEMPLATE}\n\n{user_message}',
                }
            ],
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f'    Anthropic-Fehler: {e}')
        return raw_description


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

                title       = job.get('title', '')
                company     = job.get('company', '')
                raw_desc    = job.get('description', '')

                print(f"    Beschreibung anreichern: {title} @ {company}")
                enriched_desc = enrich_description(title, company, raw_desc)

                all_jobs.append({
                    'id':          job.get('id', ''),
                    'title':       title,
                    'company':     company,
                    'locations':   job.get('locations', ''),
                    'date':        job.get('date', ''),
                    'salary':      job.get('salary', ''),
                    'description': enriched_desc,
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
