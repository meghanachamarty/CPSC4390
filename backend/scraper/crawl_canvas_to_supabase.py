#!/usr/bin/env python3
import os, re, json, signal, concurrent.futures, threading, html as html_lib
from pathlib import Path
from urllib.parse import unquote, urlparse, urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from typing import Optional, Tuple, List, Dict, Set
from playwright.sync_api import sync_playwright
import requests
from requests.adapters import HTTPAdapter, Retry

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Make sure environment variables are set manually.")

def _load_env_vars():
    global ANON, SUPABASE_URL, STORAGE_BUCKET
    ANON = os.environ.get("SUPABASE_ANON_KEY")
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET")
    
    if not ANON:
        print("🚨 SUPABASE_ANON_KEY not found in environment variables")
    if not SUPABASE_URL:
        print("🚨 SUPABASE_URL not found in environment variables")
    if not STORAGE_BUCKET:
        print("🚨 STORAGE_BUCKET not found in environment variables")

_load_env_vars() # Load variables at the start

# ===== CONFIG =====
CANVAS_BASE = "https://yale.instructure.com"
EDGE_FN_URL = f"{SUPABASE_URL}/functions/v1/ingest_by_url" if SUPABASE_URL else "https://mojqfejmiuzqqskprcrr.supabase.co/functions/v1/ingest_by_url"

# Fix 1: Ensure headers are set only if the key is available.
FN_HEADERS = {"Authorization": f"Bearer {ANON}"} if ANON else {}

TERM_PATTERNS = [r"Fall\s*2025", r"\bFA\s*25\b"]
EXTENSIONS = re.compile(r"\.(pdf|doc|docx|ppt|pptx|xls|xlsx|png|jpg|jpeg|heic)$", re.I)

FOLDER_LINK_RE = re.compile(r'href="(/courses/\d+/files/folder[^"]*)"')
PAGINATION_RE  = re.compile(r'href="(/courses/\d+/files[^"]*?[?&]page=\d+[^"]*)"')
FILENAME_RE = re.compile(r'filename\*?=(?:UTF-8\'\')?(.+)$', re.I)

FILE_ID_RE = re.compile(r"/courses/(\d+)/files/(\d+)")
VERSION_LINK_RE = re.compile(r'href="([^"]*?/files/\d+/(?:download|[^"]*?\bver=\d+)[^"]*)"', re.I)

# ===== THREAD-LOCAL HTTP SESSIONS =====
_thread_local = threading.local()

def _make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["GET", "HEAD", "POST", "PUT"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def get_canvas_session() -> requests.Session:
    s = getattr(_thread_local, "canvas_s", None)
    if s is None:
        s = _make_session()
        _thread_local.canvas_s = s
    return s

def get_supabase_session() -> requests.Session:
    s = getattr(_thread_local, "supabase_s", None)
    if s is None:
        s = _make_session()
        _thread_local.supabase_s = s
    return s

# ===== HELPERS =====
def abs_url(href: str) -> str:
    return urljoin(CANVAS_BASE + "/", href)

def filename_from_headers(effective_url: str, headers: dict) -> str:
    cd = headers.get("content-disposition") or headers.get("Content-Disposition") or ""
    m = FILENAME_RE.search(cd)
    if m:
        return unquote(m.group(1).strip().strip('"'))
    path_name = unquote(Path(urlparse(effective_url).path).name or "")
    if path_name and "." not in path_name:
        path_name += ".pdf"
    return path_name or "file.pdf"

# Fix 2: Reduced max length from 180 to a much safer 80 characters.
def safe_name(s: str) -> str:
    return re.sub(r"[^\w.\- ()]+", "_", s).strip()[:80] 

def is_login_page(url: str, html: str) -> bool:
    u = url.lower()
    if any(k in u for k in ("/login", "idp", "sso", "shib", "duo", "authenticate")):
        return True
    return bool(re.search(r"password|duo|shibboleth|single sign[- ]on", html, re.I))

def ensure_download(u: str) -> str:
    m = re.search(r"/courses/(\d+)/files/(\d+)", u)
    if m:
        c, fid = m.groups()
        return f"{CANVAS_BASE}/courses/{c}/files/{fid}/download"
    m = re.search(r"/files/(\d+)", u)
    if m:
        fid = m.group(1)
        return f"{CANVAS_BASE}/files/{fid}/download"
    return u

def extract_links_from_html(html: str) -> Set[str]:
    hrefs = set(re.findall(r'href="([^"]+)"', html))
    out = set()
    for h in hrefs:
        u = abs_url(h)
        if EXTENSIONS.search(u) or re.search(r"/files/\d+(?:/download)?(?:$|[?#])", u):
            out.add(u)
    return out

def html_of(ctx, path_or_abs: str) -> str:
    target = path_or_abs if path_or_abs.startswith("http") else abs_url(path_or_abs)
    resp = ctx.request.get(target)
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status} for {target}")
    html = resp.text()
    if is_login_page(resp.url, html):
        raise RuntimeError("Redirected to login (auth expired)")
    return html

# ===== URL CANONICALIZATION =====
def canonicalize_folder_or_page(u: str) -> str:
    u = abs_url(u)
    u = html_lib.unescape(u)
    u = unquote(u)
    parts = urlsplit(u)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() == "page"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), urlencode(kept, doseq=True), ""))

# ===== SUPABASE =====
def get_signed_upload_url(path: str, content_type: str) -> Optional[str]:
    if not FN_HEADERS:
        raise RuntimeError("Supabase Authorization key is missing. Set SUPABASE_ANON_KEY environment variable.")
    
    if not EDGE_FN_URL:
        raise RuntimeError("EDGE_FN_URL is not configured. Check SUPABASE_URL environment variable.")
        
    s = get_supabase_session()
    payload = {"path": path.lstrip("/"), "contentType": content_type or "application/octet-stream"}

    
    try:
        r = s.post(
            EDGE_FN_URL,
            json=payload,
            headers=FN_HEADERS,
            timeout=60,
        )
        
        
        if not r.ok:
            if r.status_code in (400, 409):
                try:
                    err_data = r.json()
                    err = err_data.get("error", "")

                    if "already exists" in err:
                        return None
                except json.JSONDecodeError:
                    print(f"  Raw error response: {r.text}")
            else:
                print(f"  Function error (status {r.status_code}): {r.text}")
            r.raise_for_status()
            
        data = r.json()
        print(f"  Response data keys: {list(data.keys())}")
        
        if "url" not in data:
            raise RuntimeError(f"No signed URL in response: {data}")
        return data["url"]
        
    except requests.exceptions.RequestException as e:
        print(f"  Network error calling Supabase function: {e}")
        raise
    except Exception as e:
        print(f"  Unexpected error in get_signed_upload_url: {e}")
        raise

# ===== VERSION EXPANSION =====
def _requests_get_html(url: str, cookies: Dict[str, str]) -> str:
    s = get_canvas_session()
    prep = s.prepare_request(requests.Request("GET", url))
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    if cookie_str:
        prep.headers["Cookie"] = cookie_str
    resp = s.send(prep, timeout=60, allow_redirects=True)
    resp.raise_for_status()
    t = resp.text
    if is_login_page(resp.url, t):
        raise RuntimeError("Redirected to login (auth expired)")
    return t

def expand_file_versions_via_requests(course_id: str, file_id: str, cookies: Dict[str, str]) -> List[str]:
    url = f"{CANVAS_BASE}/courses/{course_id}/files/{file_id}"
    html = _requests_get_html(url, cookies)
    urls = set(urljoin(CANVAS_BASE + "/", rel) for rel in VERSION_LINK_RE.findall(html))
    if not urls:
        for rel in re.findall(r'href="([^"]+)"', html):
            if f"/files/{file_id}" in rel and ("download" in rel or "ver=" in rel):
                urls.add(urljoin(CANVAS_BASE + "/", rel))
    if not urls:
        urls.add(f"{CANVAS_BASE}/courses/{course_id}/files/{file_id}/download")
    return list(urls)

def _expand_one_version(args: Tuple[str, str, Dict[str, str]]) -> List[str]:
    c, f, cookies = args
    try:
        return expand_file_versions_via_requests(c, f, cookies)
    except Exception:
        return []

# ===== SCRAPERS (Functions unchanged, only list_courses_no_api updated) =====
def crawl_modules_tab(ctx, cid):     return extract_links_from_html(html_of(ctx, f"/courses/{cid}/modules"))
def crawl_assignments_tab(ctx, cid): return extract_links_from_html(html_of(ctx, f"/courses/{cid}/assignments"))
def crawl_syllabus(ctx, cid):        return extract_links_from_html(html_of(ctx, f"/courses/{cid}/assignments/syllabus"))

def extract_files_and_folders(html: str):
    file_links = extract_links_from_html(html)
    raw_folders = set(abs_url(h) for h in FOLDER_LINK_RE.findall(html))
    raw_pages   = set(abs_url(h) for h in PAGINATION_RE.findall(html))
    folders = set(canonicalize_folder_or_page(u) for u in raw_folders)
    pages   = set(canonicalize_folder_or_page(u) for u in raw_pages)
    return file_links, folders, pages

def crawl_files_tab_recursive(page, cid: str, max_depth: int = 8):
    start = canonicalize_folder_or_page(f"/courses/{cid}/files")
    q, seen, results = [start], {start}, set()
    depth = 0
    while q and depth < max_depth:
        next_q = []
        for url in q:
            try:
                page.goto(url, wait_until="load")
                rows = page.eval_on_selector_all('div.ef-item-row', 'els => els.length') or 0
                if rows == 0:
                    try:
                        page.wait_for_selector('div[class="ef-item-row"]', timeout=1500)
                    except Exception:
                        pass
                    rows = page.eval_on_selector_all('div.ef-item-row', 'els => els.length') or 0
                    if rows == 0:
                        _force_lazy_load(page)
                html = page.content()
                files, folders, pages = extract_files_and_folders(html)
                results |= files
                for f in (folders | pages):
                    c = canonicalize_folder_or_page(f)
                    if c not in seen:
                        seen.add(c)
                        next_q.append(c)
            except Exception as e:
                print(f"  (Warn: Failed to crawl {url}: {e})")
        q, depth = next_q, depth + 1
    return results

def crawl_pages_recursive(ctx, page, cid: str, max_pages: int = 30, max_depth: int = 1):
    start_index = abs_url(f"/courses/{cid}/pages")
    results, seen_pages, q = set(), set(), []
    page.goto(start_index, wait_until="load")
    _force_lazy_load(page, max_scrolls=8, settle_checks=2)
    hrefs = page.evaluate("""() => Array.from(
      document.querySelectorAll('a[href*="/courses/"][href*="/pages/"]'),
      a => a.getAttribute('href')
    )""") or []
    index_html = page.content()
    hrefs += re.findall(r"href=['\"](/courses/\\d+/pages/[^'\"#?]+)['\"]", index_html, flags=re.I)
    for href in hrefs:
        u = abs_url(href)
        m = re.search(r"/courses/(\d+)/pages/", u)
        if m and m.group(1) == str(cid) and u not in seen_pages:
            seen_pages.add(u)
            q.append((u, 0))
    while q and len(seen_pages) < max_pages:
        u, d = q.pop(0)
        if d >= max_depth:
            continue
        try:
            html = html_of(ctx, u)
            results |= extract_links_from_html(html)
            for href in re.findall(r"href=['\"](/courses/\\d+/pages/[^'\"#?]+)['\"]", html, flags=re.I):
                u_new = abs_url(href)
                m = re.search(r"/courses/(\d+)/pages/", u_new)
                if m and m.group(1) == str(cid) and u_new not in seen_pages and len(seen_pages) < max_pages:
                    seen_pages.add(u_new)
                    q.append((u_new, d + 1))
        except Exception as e:
            print(f"  (Warn: could not crawl page {u}: {e})")
    return results

def _force_lazy_load(page, max_scrolls=12, dy=2400, settle_checks=2, escalate_to: int = 30):
    def do_scrolls(limit):
        page.wait_for_load_state("load")
        last_count, stable = -1, 0
        for _ in range(limit):
            page.mouse.wheel(0, dy)
            page.wait_for_timeout(60)
            count = page.eval_on_selector_all('div.ef-item-row', 'els => els.length') or 0
            if count == last_count:
                stable += 1
                if stable >= settle_checks:
                    break
            else:
                stable, last_count = 0, count
        page.wait_for_load_state("load")
        return last_count
    rows = do_scrolls(max_scrolls)
    if rows == 0 and escalate_to and escalate_to > max_scrolls:
        rows = do_scrolls(escalate_to)
    return rows

# ===== LOGIN / COURSES (Fixed) =====
def ensure_logged_in(pw, browser, ctx):
    page = ctx.new_page()
    page.goto(f"{CANVAS_BASE}/", wait_until="load")
    if is_login_page(page.url, page.content()):
        print("\nSession expired. Opening a window for SSO…")
        b2 = pw.chromium.launch(headless=False)
        c2 = b2.new_context()
        pg = c2.new_page()
        pg.goto(f"{CANVAS_BASE}/", wait_until="load")
        input("Complete SSO/DUO in the opened window, then press Enter here…")
        c2.storage_state(path="storage_state.json")
        b2.close()
        ctx.close()
        return browser.new_context(storage_state="storage_state.json")
    page.close()
    return ctx

def list_courses_no_api(page) -> Dict[str, str]:
    courses: Dict[str, str] = {}
    page.goto(f"{CANVAS_BASE}/", wait_until="load")
    dash_html = page.content()
    
    # Fix 3: More aggressive title cleaning to prevent excessive path length.
    def clean_title(raw_title: str, cid: str) -> str:
        # 1. Take only the first line/component
        title = raw_title.strip().splitlines()[0].strip()
        
        # 2. Aggressive cleanup for redundancy (e.g., CPSC 4390...CPSC 4390...)
        
        # Look for the last colon or closing parenthesis, which usually marks the end
        # of the descriptive part of the title.
        last_paren = title.rfind(")")
        last_colon = title.rfind(":")
        
        if last_paren > -1:
            # Keep up to the closing parenthesis
            title = title[:last_paren + 1].strip()
        elif last_colon > -1:
            # Keep up to the colon
            title = title[:last_colon].strip()
            
        # Fallback: Truncate at the first sign of repetition of the course code/term
        if len(title) > 80:
             # Find the first mention of a 4-letter + 4-digit code (e.g., CPSC 4390)
             match = re.search(r'(\b\w{4}\s*\d{4})', title, re.I)
             if match:
                 # Look for the *second* instance of that code, and truncate before it
                 code = match.group(1)
                 second_instance = title.find(code, match.end())
                 if second_instance > -1:
                     title = title[:second_instance].strip()

        return title or f"Course {cid}"

    for href in re.findall(r'href="(/courses/\d+)"', dash_html):
        cid = re.search(r"/courses/(\d+)", href).group(1)
        try:
            raw_title = (page.locator(f'a[href="{href}"]').first.text_content() or f"Course {cid}")
            courses[cid] = clean_title(raw_title, cid)
        except Exception:
            courses[cid] = f"Course {cid}"

    # Also check the /courses list page
    page.goto(f"{CANVAS_BASE}/courses", wait_until="load")
    courses_html = page.content()
    for href in re.findall(r'href="(/courses/\d+)"', courses_html):
        cid = re.search(r"/courses/(\d+)", href).group(1)
        try:
            raw_title = (page.locator(f'a[href="{href}"]').first.text_content() or f"Course {cid}")
            courses.setdefault(cid, clean_title(raw_title, cid))
        except Exception:
            courses.setdefault(cid, f"Course {cid}")

    # Fallback/Alt pages check
    if not courses:
        page.goto(f"{CANVAS_BASE}/courses?include[]=published", wait_until="load")
        alt_html = page.content()
        for href in re.findall(r'href="(/courses/\d+)"', alt_html):
            cid = re.search(r"/courses/(\d+)", href).group(1)
            try:
                raw_title = (page.locator(f'a[href="{href}"]').first.text_content() or f"Course {cid}")
                courses.setdefault(cid, clean_title(raw_title, cid))
            except Exception:
                courses.setdefault(cid, f"Course {cid}")

    # Filter to Fall 2025 if detectable on the course homepage
    fall = {}
    for cid, title in courses.items():
        try:
            page.goto(f"{CANVAS_BASE}/courses/{cid}", wait_until="load")
            html = page.content()
            if any(re.search(p, html, re.I) for p in TERM_PATTERNS):
                fall[cid] = title
            page.wait_for_timeout(60)
        except Exception:
            pass
    return fall or courses

# ===== DOWNLOAD + UPLOAD WORKER =====
def _download_and_upload(u: str, cookies: Dict[str, str], safe_course: str, term_folder: str) -> str:
    # Check for authorization key before starting download/upload
    if not ANON:
        return f"  ✗ {u} — ERROR: SUPABASE_ANON_KEY is missing. Cannot upload."
    
    if not SUPABASE_URL:
        return f"  ✗ {u} — ERROR: SUPABASE_URL is missing. Cannot upload."
        
    try:
        canvas_s = get_canvas_session()
        supabase_s = get_supabase_session()

        prep = canvas_s.prepare_request(requests.Request("GET", u))
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        if cookie_str:
            prep.headers["Cookie"] = cookie_str

        with canvas_s.send(prep, stream=True, timeout=120, allow_redirects=True) as resp_get:
            resp_get.raise_for_status()
            headers = resp_get.headers
            content_type = headers.get("content-type", "application/octet-stream")
            content_len = headers.get("content-length")
            size_hint = int(content_len) if content_len and content_len.isdigit() else None
            filename = safe_name(filename_from_headers(resp_get.url, headers))
            
            # The full path to the file in Supabase Storage
            path = f"Canvas/{term_folder}/{safe_course}/{filename}"

            try:
                signed = get_signed_upload_url(path, content_type)
                if signed is None:
                    return f"  - {filename} (already exists)"
            except Exception as e:
                return f"  ✗ {filename} — Failed to get signed URL: {e}"

            def gen():
                total = 0
                for chunk in resp_get.iter_content(chunk_size=65536):
                    if chunk:
                        total += len(chunk)
                        yield chunk
                gen.total = total  # type: ignore
            gen.total = 0  # type: ignore

            up = supabase_s.put(signed, data=gen(), headers={"Content-Type": content_type}, timeout=300)
            up.raise_for_status()

            mb = (gen.total / (1024*1024)) if gen.total else (size_hint / (1024*1024) if size_hint else 0)
            size_str = f"{mb:.2f} MB" if mb else ("unknown size" if size_hint is None else f"{size_hint} B")
            return f"  ✓ {filename} ({content_type}) [{size_str}]"
    except Exception as e:
        return f"  ✗ {u} — {e}"

# ===== MAIN =====
def run():
    signal.signal(signal.SIGINT, lambda *_: exit(1))
    
    # Debug: Print environment variable status
    print(f"\n=== Environment Check ===")
    print(f"SUPABASE_ANON_KEY: {'SET' if ANON else 'NOT SET'}")
    print(f"SUPABASE_URL: {'SET' if SUPABASE_URL else 'NOT SET'}")
    print(f"STORAGE_BUCKET: {'SET' if STORAGE_BUCKET else 'NOT SET'}")
    print(f"EDGE_FN_URL: {EDGE_FN_URL}")
    
    if not ANON:
        print("\n🚨 CRITICAL ERROR: SUPABASE_ANON_KEY environment variable is not set.")
        print("Please check your .env file or export the key manually.")
        return
        
    if not SUPABASE_URL:
        print("\n🚨 CRITICAL ERROR: SUPABASE_URL environment variable is not set.")
        print("Please check your .env file or export the URL manually.")
        return
        
    with sync_playwright() as pw:
        # Ensure Playwright launches a browser context, which is necessary for the Canvas session
        browser = pw.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(storage_state="storage_state.json")
            ctx = ensure_logged_in(pw, browser, ctx)
            page = ctx.new_page()

            courses = list_courses_no_api(page)
            print(f"Found {len(courses)} course(s) by HTML scrape")
            if not courses:
                print("No courses visible. Check CANVAS_BASE and re-run login_once.py.")
                return

            for cid, title in courses.items():
                safe_course = safe_name(title)
                print(f"== {title} ({cid}) ==")

                links: Set[str] = set()

                try:
                    links |= crawl_files_tab_recursive(page, cid)
                except Exception as e:
                    print(f"  (skip crawl_files_tab_recursive: {e})")

                for fn in (crawl_modules_tab, crawl_assignments_tab, crawl_syllabus):
                    try:
                        links |= fn(ctx, cid)
                    except Exception as e:
                        print(f"  (skip {fn.__name__}: {e})")

                try:
                    links |= crawl_pages_recursive(ctx, page, cid, max_pages=30, max_depth=1)
                except Exception as e:
                    print(f"  (skip crawl_pages_recursive: {e})")

                targets: Set[str] = set()
                file_ids: Dict[Tuple[str, str], None] = {}
                for u in links:
                    if urlparse(u).netloc != urlparse(CANVAS_BASE).netloc:
                        continue
                    m = FILE_ID_RE.search(u)
                    if m:
                        file_ids[(m.group(1), m.group(2))] = None
                    elif EXTENSIONS.search(u) or "/files/" in u:
                        targets.add(u)

                cookies_list = ctx.cookies()
                requests_cookies = {c['name']: c['value'] for c in cookies_list}

                print(f"  Found {len(file_ids)} unique file IDs to expand…")
                if file_ids:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                        args = [(c, f, requests_cookies) for (c, f) in file_ids.keys()]
                        for urls in pool.map(_expand_one_version, args):
                            targets.update(urls)

                # Normalize to /download endpoints and dedup
                targets = list({ensure_download(u) for u in targets})

                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                    futures = [pool.submit(_download_and_upload, u, requests_cookies, safe_course, "Fall 2025")
                               for u in sorted(targets)]
                    for fut in concurrent.futures.as_completed(futures):
                        print(fut.result())

        finally:
            browser.close()

if __name__ == "__main__":
    run()