import requests
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin

BACKEND_URL = 'https://lebenplus-backend.onrender.com/api/jobs'
PAGE_SIZE   = 20
PAGES       = 10

KATEGORIEN = [
    { 'name': 'pflege', 'keywords': 'Pflege', 'location': 'Schweiz', 'output': 'data/pflege-jobs.json' },
    { 'name': 'sap',    'keywords': 'SAP',    'location': 'Schweiz', 'output': 'data/sap-jobs.json' },
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
    'Accept-Language': 'de-CH,de;q=0.9',
    'Accept': 'text/html,application/xhtml+xml',
}

def fetch_full_description(job_url):
    """Folgt dem Redirect und holt die volle Beschreibung von der Zielseite."""
    try:
        # Redirect zu Careerjet.ch oder Arbeitgeber-Seite folgen
        r = requests.get(job_url, headers=HEADERS, timeout=15, allow_redirects=True)
        final_url = r.url
        html = r.text

        # Falls wir auf Careerjet gelandet sind
        if 'careerjet.ch' in final_url or 'careerjet.com' in final_url:
            # Beschreibung aus Careerjet-Jobseite extrahieren
            # Alles nach dem h1 bis zu einem bestimmten Abschnitt
            match = re.search(r'<h1[^>]*>.*?</h1>(.*?)(?:<div[^>]*class="[^"]*apply|<footer|Arbeitssuchende)', html, re.DOTALL)
            if match:
                desc = match.group(1)
            else:
                # Breiter suchen
                match = re.search(r'(?:Vollzeit|Teilzeit|Unbefristet)[^<]*</[^>]+>(.*?)(?:Arbeitssuchende|<footer)', html, re.DOTALL)
                desc = match.group(1) if match else html
        else:
            # Allgemeine Extraktion für andere Seiten
            # Versuche den Hauptinhalt zu finden
            for pattern in [
                r'<article[^>]*>(.*?)</article>',
                r'<div[^>]*class="[^"]*job[^"]*description[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
            ]:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    desc = match.group(1)
                    break
            else:
                return None

        # HTML zu lesbarem Text konvertieren
        desc = re.sub(r'<script[^>]*>.*?</script>', '', desc, flags=re.DOTALL)
        desc = re.sub(r'<style[^>]*>.*?</style>', '', desc, flags=re.DOTALL)
        desc = re.sub(r'<li[^>]*>', '• ', desc)
        desc = re.sub(r'</li>', '\n', desc)
        desc = re.sub(r'<br\s*/?>', '\n', desc)
        desc = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\1\n', desc)
        desc = re.sub(r'<p[^>]*>', '\n', desc)
        desc = re.sub(r'</p>', '\n', desc)
        desc = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', desc)
        desc = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', desc)
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = re.sub(r'[ \t]+', ' ', desc)
        desc = re.sub(r'\n{3,}', '\n\n', desc)
        desc = desc.strip()

        if len(desc) > 300:
            return desc
        return None

    except Exception as e:
        print(f"    Fehler: {e}")
        return None

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

    # Volle Beschreibungen laden
    print(f"\n  Lade Beschreibungen für {len(all_jobs)} Jobs...")
    for i, job in enumerate(all_jobs):
        print(f"  [{i+1}/{len(all_jobs)}] {job['title'][:45]}...")
        full = fetch_full_description(job['url'])
        if full:
            job['description'] = full
            print(f"    ✅ {len(full)} Zeichen")
        else:
            print(f"    ⚠️  Kurzbeschreibung behalten")
        time.sleep(0.5)

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
        print(f"Gespeichert: {kat['output']} ✅")

if __name__ == '__main__':
    main()
