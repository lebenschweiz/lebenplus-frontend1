import requests
import json
import os
from datetime import datetime
import anthropic

BACKEND_URL = 'https://lebenplus-backend.onrender.com/api/jobs'
PAGE_SIZE   = 20
PAGES       = 10
MAX_JOBS    = 10

KATEGORIEN = [
    { 'name': 'pflege', 'keywords': 'Pflege', 'location': 'Schweiz', 'output': 'data/pflege-jobs.json' },
    { 'name': 'sap',    'keywords': 'SAP',    'location': 'Schweiz', 'output': 'data/sap-jobs.json' },
]

ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'

PROMPT_TEMPLATE = (
    'Du erhältst einen Ausschnitt einer Stellenbeschreibung. '
    'Deine Aufgabe: '
    '1) Entferne alle Telefonnummern, E-Mail-Adressen, URLs und Kontaktangaben '
    '2) Schreibe abgeschnittene Sätze zu Ende basierend nur auf dem vorhandenen Kontext '
    '3) Strukturiere den Text mit Abschnitten wie \'Über die Stelle\', \'Ihre Aufgaben\', \'Ihr Profil\', \'Wir bieten\' - aber nur wenn diese Informationen im Originaltext vorhanden sind '
    '4) Erfinde KEINE neuen Informationen, Anforderungen oder Benefits die nicht im Originaltext stehen '
    '5) Behalte alle originalen Formulierungen so nah wie möglich '
    '6) Gib nur den aufbereiteten Text zurück ohne Markdown-Symbole oder Erklärungen.'
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
        if len(all_jobs) >= MAX_JOBS:
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
                if len(all_jobs) >= MAX_JOBS:
                    break

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

    all_combined = []
    now_str = datetime.now().strftime('%d.%m.%Y %H:%M')

    for kat in KATEGORIEN:
        print(f"\n=== {kat['name'].upper()} ===")
        jobs = fetch_jobs(kat['keywords'], kat['location'])
        print(f"\nGesamt: {len(jobs)} Jobs")
        output = {
            'updated': now_str,
            'total':   len(jobs),
            'jobs':    jobs,
        }
        with open(kat['output'], 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Gespeichert: {kat['output']}")
        all_combined.extend(jobs)

    # Kombinierte jobs.json für das Frontend
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
