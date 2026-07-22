"""
Script 04: Web Scraping Vietnamese Medical Data
Sources: Vinmec, HelloBacsi, Long Chau, Medlatec
Output: datasets/scraped/*.json
"""
import json
import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(PROJECT_ROOT, "datasets", "scraped")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_text(text: str) -> str:
    """Clean scraped text."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def fetch_page(url: str, timeout: int = 15) -> str:
    """Fetch a page with retry logic."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                return resp.text
            print(f"  HTTP {resp.status_code} for {url}")
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for {url}: {e}")
            time.sleep(2 * (attempt + 1))
    return ""


# ============================================================
# VINMEC
# ============================================================
def scrape_vinmec_diseases():
    """Scrape disease information from Vinmec."""
    print("=== Scraping Vinmec Diseases ===")
    base_url = "https://www.vinmec.com"
    disease_index_url = f"{base_url}/vi/benh/"

    html = fetch_page(disease_index_url)
    if not html:
        print("Failed to fetch Vinmec disease index")
        return []

    soup = BeautifulSoup(html, "html.parser")
    disease_links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/vi/benh/" in href and href != "/vi/benh/":
            full_url = urljoin(base_url, href)
            if full_url not in disease_links:
                disease_links.append(full_url)

    print(f"Found {len(disease_links)} disease links")

    results = []
    for i, url in enumerate(disease_links[:50]):
        print(f"  Scraping {i+1}/{min(50, len(disease_links))}: {url}")
        html = fetch_page(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        title_text = clean_text(title.get_text()) if title else ""

        content_div = soup.find("div", class_=re.compile(r"content|article|body", re.I))
        if not content_div:
            content_div = soup.find("article")

        if content_div:
            paragraphs = content_div.find_all(["p", "li"])
            content_parts = []
            for p in paragraphs:
                text = clean_text(p.get_text())
                if len(text) > 10:
                    content_parts.append(text)
            content = " ".join(content_parts[:20])

            if title_text and len(content) > 50:
                results.append({
                    "source": "vinmec",
                    "url": url,
                    "title": title_text,
                    "content": content[:2000],
                    "type": "disease_info"
                })

        time.sleep(random.uniform(1, 2))

    return results


def scrape_vinmec_symptoms():
    """Scrape symptom information from Vinmec."""
    print("=== Scraping Vinmec Symptoms ===")
    base_url = "https://www.vinmec.com"
    symptom_index = f"{base_url}/vi/tin-tuc/suc-khoe/bieu-hieu-nhan-biet/"

    html = fetch_page(symptom_index)
    if not html:
        print("Failed to fetch symptom index")
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/vi/tin-tuc/" in href:
            full_url = urljoin(base_url, href)
            if full_url not in links:
                links.append(full_url)

    results = []
    for i, url in enumerate(links[:30]):
        print(f"  Scraping symptom {i+1}/{min(30, len(links))}: {url}")
        html = fetch_page(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        title_text = clean_text(title.get_text()) if title else ""

        content_div = soup.find("div", class_=re.compile(r"content|article", re.I))
        if content_div:
            paragraphs = content_div.find_all("p")
            content = " ".join(clean_text(p.get_text()) for p in paragraphs if len(clean_text(p.get_text())) > 10)
            if title_text and len(content) > 50:
                results.append({
                    "source": "vinmec",
                    "url": url,
                    "title": title_text,
                    "content": content[:2000],
                    "type": "symptom_info"
                })

        time.sleep(random.uniform(1, 2))

    return results


# ============================================================
# HELLOBACSI
# ============================================================
def scrape_helloBacsi_diseases():
    """Scrape disease info from HelloBacSi."""
    print("=== Scraping HelloBacSi Diseases ===")
    base_url = "https://www.hellobacsi.com"
    disease_url = f"{base_url}/benh/"

    html = fetch_page(disease_url)
    if not html:
        print("Failed to fetch HelloBacSi disease index")
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/benh/" in href and href != "/benh/":
            full_url = urljoin(base_url, href)
            if full_url not in links:
                links.append(full_url)

    print(f"Found {len(links)} HelloBacSi disease links")

    results = []
    for i, url in enumerate(links[:50]):
        print(f"  Scraping {i+1}/{min(50, len(links))}: {url}")
        html = fetch_page(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        title_text = clean_text(title.get_text()) if title else ""

        content_div = soup.find("div", class_=re.compile(r"content|article|body", re.I))
        if content_div:
            paragraphs = content_div.find_all(["p", "li"])
            content_parts = []
            for p in paragraphs:
                text = clean_text(p.get_text())
                if len(text) > 10:
                    content_parts.append(text)
            content = " ".join(content_parts[:20])

            if title_text and len(content) > 50:
                results.append({
                    "source": "hellobacsi",
                    "url": url,
                    "title": title_text,
                    "content": content[:2000],
                    "type": "disease_info"
                })

        time.sleep(random.uniform(1, 2))

    return results


# ============================================================
# LONG CHAU PHARMACY
# ============================================================
def scrape_longchau_medications():
    """Scrape medication info from Long Chau."""
    print("=== Scraping Long Chau Medications ===")
    base_url = "https://nhathuoclongchau.com"
    drug_url = f"{base_url}/thuoc"

    html = fetch_page(drug_url)
    if not html:
        print("Failed to fetch Long Chau drug index")
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/thuoc/" in href and href != "/thuoc/":
            full_url = urljoin(base_url, href)
            if full_url not in links:
                links.append(full_url)

    print(f"Found {len(links)} Long Chau drug links")

    results = []
    for i, url in enumerate(links[:50]):
        print(f"  Scraping drug {i+1}/{min(50, len(links))}: {url}")
        html = fetch_page(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        title_text = clean_text(title.get_text()) if title else ""

        info_div = soup.find("div", class_=re.compile(r"product-info|drug-info|content", re.I))
        if info_div:
            paragraphs = info_div.find_all(["p", "li", "span"])
            content_parts = []
            for p in paragraphs:
                text = clean_text(p.get_text())
                if len(text) > 5:
                    content_parts.append(text)
            content = " ".join(content_parts[:30])

            if title_text and len(content) > 20:
                results.append({
                    "source": "longchau",
                    "url": url,
                    "title": title_text,
                    "content": content[:2000],
                    "type": "medication_info"
                })

        time.sleep(random.uniform(1, 2))

    return results


# ============================================================
# DOCTOR Q&A FORUMS
# ============================================================
def scrape_doctor_qa():
    """Scrape doctor Q&A for natural clinical text."""
    print("=== Scraping Doctor Q&A ===")
    base_url = "https://www.hellobacsi.com"
    qa_url = f"{base_url}/hoi-dap/"

    html = fetch_page(qa_url)
    if not html:
        print("Failed to fetch Q&A index")
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/hoi-dap/" in href:
            full_url = urljoin(base_url, href)
            if full_url not in links:
                links.append(full_url)

    results = []
    for i, url in enumerate(links[:40]):
        print(f"  Scraping Q&A {i+1}/{min(40, len(links))}: {url}")
        html = fetch_page(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        question_div = soup.find("div", class_=re.compile(r"question|content", re.I))
        if question_div:
            text = clean_text(question_div.get_text())
            if len(text) > 20:
                results.append({
                    "source": "hellobacsi_qa",
                    "url": url,
                    "content": text[:2000],
                    "type": "patient_question"
                })

        time.sleep(random.uniform(1, 2))

    return results


# ============================================================
# MAIN
# ============================================================
def save_results(results: list, filename: str):
    """Save results to JSON."""
    os.makedirs(DATASETS_DIR, exist_ok=True)
    filepath = os.path.join(DATASETS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(results)} items to {filepath}")


if __name__ == "__main__":
    os.makedirs(DATASETS_DIR, exist_ok=True)

    all_results = {}

    # Vinmec
    vinmec_diseases = scrape_vinmec_diseases()
    save_results(vinmec_diseases, "vinmec_diseases.json")
    all_results["vinmec_diseases"] = len(vinmec_diseases)

    vinmec_symptoms = scrape_vinmec_symptoms()
    save_results(vinmec_symptoms, "vinmec_symptoms.json")
    all_results["vinmec_symptoms"] = len(vinmec_symptoms)

    # HelloBacSi
    hellobacsi_diseases = scrape_helloBacsi_diseases()
    save_results(hellobacsi_diseases, "hellobacsi_diseases.json")
    all_results["hellobacsi_diseases"] = len(hellobacsi_diseases)

    # Long Chau
    longchau_drugs = scrape_longchau_medications()
    save_results(longchau_drugs, "longchau_medications.json")
    all_results["longchau_drugs"] = len(longchau_drugs)

    # Doctor Q&A
    doctor_qa = scrape_doctor_qa()
    save_results(doctor_qa, "doctor_qa.json")
    all_results["doctor_qa"] = len(doctor_qa)

    print("\n=== Scraping Summary ===")
    for source, count in all_results.items():
        print(f"  {source}: {count} items")
