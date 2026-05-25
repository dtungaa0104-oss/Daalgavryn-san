"""
eContent.edu.mn — Сурах бичгийн жагсаалт татах
Нийтэд нээлттэй, нэвтрэлт шаарддаггүй хуудаснаас
ангийн номын жагсаалтыг авна.
"""
import requests
from bs4 import BeautifulSoup
import re

BASE = "https://econtent.edu.mn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OrkhontulEBS/1.0)"
}

def get_books_by_grade(grade: int) -> list[dict]:
    """Тухайн ангийн бүх номын жагсаалтыг буцаана."""
    url = f"{BASE}/book/{grade}rangi"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    books = []

    # Ном бүрийн линк + нэр
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/pages/more.php?id=' in href or '/book/' in href:
            title_el = a.find(['h2', 'h3', 'strong', 'span'])
            title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
            title = re.sub(r'\s+', ' ', title).strip()
            if not title or len(title) < 3:
                continue
            full_url = href if href.startswith('http') else BASE + href
            books.append({
                'id':    re.search(r'id=(\d+)', href).group(1) if 'id=' in href else '',
                'title': title,
                'url':   full_url,
                'grade': grade,
            })

    # Давхардал арилгах
    seen = set()
    unique = []
    for b in books:
        key = b['url']
        if key not in seen:
            seen.add(key)
            unique.append(b)
    return unique

def get_book_detail(book_id: str) -> dict:
    """Нэг номын дэлгэрэнгүй мэдээлэл (хуудасны тоо гэх мэт)."""
    url = f"{BASE}/pages/more.php?id={book_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception:
        return {}

    soup = BeautifulSoup(r.text, 'html.parser')
    info = {'url': url, 'id': book_id}

    # Гарчиг
    h = soup.find(['h1','h2'])
    if h:
        info['title'] = h.get_text(strip=True)

    # PDF линкүүд
    pdf_links = []
    for a in soup.find_all('a', href=True):
        if a['href'].lower().endswith('.pdf') or 'pdf' in a['href'].lower():
            href = a['href']
            full = href if href.startswith('http') else BASE + '/' + href.lstrip('/')
            pdf_links.append(full)
    info['pdf_links'] = pdf_links

    # Зураг (ном хавтас)
    img = soup.find('img', src=True)
    if img:
        src = img['src']
        info['cover'] = src if src.startswith('http') else BASE + src

    return info

def search_books(grade: int, keyword: str) -> list[dict]:
    """Ангийн номнуудаас гарчигаар хайна."""
    books = get_books_by_grade(grade)
    kw = keyword.lower()
    return [b for b in books if kw in b['title'].lower()]

