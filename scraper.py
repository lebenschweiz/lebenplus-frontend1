import requests
import cloudscraper
import json
import os
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

BACKEND_URL = 'https://lebenplus-backend.onrender.com/api/jobs'
PAGE_SIZE   = 20
PAGES       = 10

KATEGORIEN = [
    { 'name': 'pflege', 'keywords': 'Pflege', 'location': 'Schweiz', 'output': 'data/pflege-jobs.json' },
    { 'name': 'sap',    'keywords': 'SAP',    'location': 'Schweiz', 'output': 'data/sap-jobs.json' },
]

# cloudscraper-Session für Anti-Bot-Schutz (jobviewtrack.com, careerjet.ch)
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

def clean_html_to_text(html_fragment):
    """Konvertiert HTML-Fragment zu lesbarem Text."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_fragment, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<li[^>]*>', '• ', text)
    text = re.sub(r'</li>', '\n', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\1\n', text)
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_careerjet_description(html):
    """Extrahiert Beschreibung von Careerjet: Text zwischen </h1> und 'Arbeitssuchende'."""
    match = re.search(r'</h1>(.*?)Arbeitssuchende', html, re.DOTALL)
    if match:
        return clean_html_to_text(match.group(1))
    return None

def extract_longest_text_block(html):
    """Extrahiert den längsten zusammenhängenden Textblock aus <p> oder <div> Tags."""
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()

    longest = ''
    for tag in soup.find_all(['p', 'div']):
        text = tag.get_text(separator='\n', strip=True)
        if len(text) > len(longest):
            longest = text

    return longest if len(longest) > 100 else None

def fetch_full_description(job_url):
    """Folgt dem jobviewtrack.com Redirect mit cloudscraper und holt die volle Beschreibung."""
    try:
        r = scraper.get(job_url, timeout=15, allow_redirects=True)
        final_url = r.url
        html = r.text

        if 'careerjet.ch' in final_url or 'careerjet.com' in final_url:
            desc = extract_careerjet_description(html)
        else:
            desc = extract_longest_text_block(html)

        if desc and len(desc) > 300:
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
    print(f"\n  Lade volle Beschreibungen für {len(all_jobs)} Jobs...")
    success = 0
    for i, job in enumerate(all_jobs):
        print(f"  [{i+1}/{len(all_jobs)}] {job['title'][:50]}...")
        full = fetch_full_description(job['url'])
        if full:
            job['description'] = full
            success += 1
            print(f"    ✅ {len(full)} Zeichen")
        else:
            print(f"    ⚠️  Kurzbeschreibung behalten")
        time.sleep(0.5)

    print(f"\n  Ergebnis: {success}/{len(all_jobs)} volle Beschreibungen geladen")
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
