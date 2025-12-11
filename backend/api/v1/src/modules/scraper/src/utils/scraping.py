"""Web scraping utilities for extracting content from websites."""

import re
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from dataclasses import dataclass
from typing import List, Set, Tuple

from src.modules.scraper.src.models.keyword_filters import (
    URL_BLOCKLIST,
    GENERIC_EXCLUDED_SUBSTRINGS,
    COOKIE_KEYWORDS,
    NAV_KEYWORDS,
    STOP_PHRASES,
    HTML_BLACKLIST_SELECTORS,
    BLOCK_TAGS
)

# HTTP Session configuration
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
})


@dataclass
class ScrapedPage:
    """Represents a scraped page with its content."""
    url: str
    title: str
    content: str


def normalize_url(url: str) -> str:
    """Remove fragment and trailing slash from URL."""
    clean_url, _ = urldefrag(url)
    return clean_url.rstrip("/")


def should_index_url(url: str) -> bool:
    """
    Check if URL should be visited and saved.
    Returns False for blocked URLs.
    """
    lower_url = url.lower()

    # Check blocklist
    if any(pattern in lower_url for pattern in URL_BLOCKLIST):
        return False

    # Check generic excluded patterns
    if any(sub in lower_url for sub in GENERIC_EXCLUDED_SUBSTRINGS):
        return False

    # Check non-HTML resources
    if any(ext in lower_url for ext in [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"]):
        return False
    if lower_url.startswith("mailto:") or lower_url.startswith("tel:") or lower_url.startswith("javascript:"):
        return False

    return True


def is_noise_block(text: str) -> bool:
    """
    Check if text block is noise (cookie banner, nav, buttons, micro-phrases).
    """
    t = text.lower().strip()
    length = len(t)

    # Cookie/privacy/consent content
    if any(k in t for k in COOKIE_KEYWORDS + NAV_KEYWORDS):
        return True

    # Very short blocks: often buttons or labels
    if length < 40 and len(t.split()) < 6:
        return True

    # Blocks with almost no letters/digits (icons, symbols)
    letters = sum(c.isalpha() for c in t)
    digits = sum(c.isdigit() for c in t)
    if letters + digits < 5:
        return True

    return False


def normalize_text(text: str) -> str:
    """
    Remove strange characters, normalize spaces and empty lines.
    """
    # Remove non-alphanumeric symbols
    text = re.sub(r"[^\wÀ-ÿ.,;:!?%€@/\-\(\)\n ]+", " ", text)
    
    # Collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Clean lines
    lines = [ln.strip() for ln in text.splitlines()]
    cleaned_lines = []
    empty_streak = 0
    
    for ln in lines:
        if ln == "":
            empty_streak += 1
            if empty_streak > 1:
                continue
        else:
            empty_streak = 0
        cleaned_lines.append(ln)

    return "\n".join(cleaned_lines).strip()


def clean_page_text(raw_text: str) -> str:
    """
    Clean extracted text by removing noise blocks and normalizing format.
    """
    if not raw_text:
        return ""

    # Split into blocks/paragraphs using double newline
    blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]

    # Filter noise blocks
    kept_blocks = [b for b in blocks if not is_noise_block(b)]

    if not kept_blocks:
        return ""

    joined = "\n\n".join(kept_blocks)
    return normalize_text(joined)


def filter_redundant_content(text: str, seen_hashes: Set[str]) -> str:
    """
    Split text into blocks. Remove long blocks that have been seen before.
    """
    if not text:
        return ""

    blocks = text.split('\n\n')
    unique_blocks = []

    for block in blocks:
        # Remove sequences of 100+ equal signs
        block = re.sub(r'={100,}', '', block)
        block_clean = block.strip()
        
        if not block_clean:
            continue

        # Check only blocks > 100 characters
        if len(block_clean) > 100:
            block_hash = hashlib.md5(block_clean.encode('utf-8')).hexdigest()
            
            if block_hash in seen_hashes:
                continue
            
            seen_hashes.add(block_hash)
        
        unique_blocks.append(block)

    return "\n\n".join(unique_blocks)


def is_product_page(soup: BeautifulSoup) -> bool:
    """Detect if page is a product/shop page."""
    body_classes = soup.body.get('class', []) if soup.body else []
    if any(cls in body_classes for cls in ['single-product', 'tax-product_cat', 'woocommerce-cart', 'woocommerce-checkout']):
        return True
    if soup.select_one("form.cart") or soup.select_one(".add_to_cart_button"):
        return True
    if soup.select_one(".price") and soup.select_one(".product_title"):
        return True
    if soup.find(attrs={"itemtype": re.compile(r"schema\.org/Product")}):
        return True
    return False


def clean_html(html: str) -> str:
    """
    Clean HTML and extract text content.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for sel in HTML_BLACKLIST_SELECTORS:
        for tag in soup.select(sel):
            tag.decompose()

    # Handle text blocks
    MARKER = "###BLOCK###"
    
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_before(MARKER)
        tag.insert_after(MARKER)

    # Handle <br> as newline
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # Extract text
    text = soup.get_text(separator=" ", strip=True)

    # Clean lines and blocks
    raw_blocks = text.split(MARKER)
    clean_blocks = []
    
    for raw_block in raw_blocks:
        lines = []
        for line in raw_block.split('\n'):
            clean_line = line.strip()
            
            if not clean_line:
                continue
                
            if len(clean_line) < 2:
                continue
            if clean_line.lower() in STOP_PHRASES:
                continue
            
            clean_line = re.sub(r'\s+', ' ', clean_line)
            lines.append(clean_line)
            
        if lines:
            clean_blocks.append(" ".join(lines))

    final_text = "\n\n".join(clean_blocks)
    return re.sub(r'\n{3,}', '\n\n', final_text)


def crawl_page(url: str, visited: Set[str], seen_content_hashes: Set[str]) -> Tuple[List[ScrapedPage], Set[str]]:
    """
    Crawl a single page and extract its content.
    
    Args:
        url: URL to crawl
        visited: Set of already visited URLs
        seen_content_hashes: Set of content hashes for deduplication
        
    Returns:
        Tuple of (list of scraped pages, set of found child URLs)
    """
    url = normalize_url(url)
    pages = []
    child_urls = set()

    if url in visited:
        return pages, child_urls
    if not should_index_url(url):
        return pages, child_urls

    visited.add(url)

    try:
        response = session.get(url, timeout=10)
        
        if response.url != url:
            final_url = normalize_url(response.url)
            if final_url != url and (final_url in visited or any(p in final_url for p in URL_BLOCKLIST)):
                return pages, child_urls
                
        response.raise_for_status()
    except Exception as e:
        print(f"   Error loading {url}: {e}")
        return pages, child_urls

    content_type = response.headers.get('Content-Type', '').lower()
    if 'text/html' not in content_type or url.endswith(".pdf"):
        return pages, child_urls

    soup = BeautifulSoup(response.text, "html.parser")
    if is_product_page(soup):
        return pages, child_urls

    # Extract and deduplicate content
    raw_text = clean_html(response.text)
    deduped_text = filter_redundant_content(raw_text, seen_content_hashes)
    final_text = clean_page_text(deduped_text)

    page_title = soup.title.string.strip() if soup.title else "No Title"

    if final_text.strip():
        pages.append(ScrapedPage(url=url, title=page_title, content=final_text))

    # Find child URLs
    for link in soup.find_all("a", href=True):
        child_url = urljoin(url, link["href"])
        child_url = normalize_url(child_url)

        # Same domain only
        if urlparse(child_url).netloc != urlparse(url).netloc:
            continue

        if should_index_url(child_url):
            child_urls.add(child_url)

    return pages, child_urls


def scrape_website(
    start_url: str, 
    max_pages: int = 100,
    progress_callback: callable = None
) -> List[ScrapedPage]:
    """
    Scrape an entire website starting from the given URL.
    
    Args:
        start_url: The starting URL to crawl
        max_pages: Maximum number of pages to scrape
        progress_callback: Optional callback function to report progress.
                          Called with (pages_scraped: int, current_url: str)
        
    Returns:
        List of ScrapedPage objects
    """
    visited: Set[str] = set()
    seen_content_hashes: Set[str] = set()
    all_pages: List[ScrapedPage] = []
    
    urls_to_visit = [normalize_url(start_url)]
    
    while urls_to_visit and len(all_pages) < max_pages:
        current_url = urls_to_visit.pop(0)
        
        if current_url in visited:
            continue
            
        print(f"[+] Visiting: {current_url}")
        pages, child_urls = crawl_page(current_url, visited, seen_content_hashes)
        
        all_pages.extend(pages)
        
        # Report progress via callback
        if progress_callback:
            progress_callback(len(all_pages), current_url)
        
        # Add child URLs to queue
        for child_url in child_urls:
            if child_url not in visited and child_url not in urls_to_visit:
                urls_to_visit.append(child_url)
    
    print(f"\nScraping completed! Total pages: {len(all_pages)}")
    return all_pages
