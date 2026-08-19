import argparse
import asyncio
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright


DEFAULT_QUERY = '(vibecoding OR "vibe coding" OR "vibe-coding" OR "vibe coded" OR "vibecode" OR "vibe coder" OR "ngoding pakai AI" OR "kode pakai AI")'
DEFAULT_QUERY_VARIANTS = [
    '("vibe coding" OR vibecoding)',
    '("vibe coding" OR vibecoding) (app OR website OR project OR startup)',
    '("vibe coding" OR vibecoding) (ai OR llm OR agent OR prompt)',
    '("vibe coding" OR vibecoding) (cursor OR windsurf OR copilot OR claude OR replit OR lovable OR bolt)',
    '("vibe coding" OR vibecoding) (bug OR debug OR ship OR build OR github OR repo)',
    '("vibe coding" OR vibecoding) lang:en',
    '("vibe coding" OR vibecoding) lang:id',
    '("ngoding pakai AI" OR "kode pakai AI" OR "coding pakai AI")',
    '"vibe coded" (app OR website OR project OR software OR ai)',
    'vibecode (app OR website OR ai OR software)',
]
DEFAULT_RELEVANT_KEYWORDS = [
    "vibecoding",
    "vibe coding",
    "vibe-coding",
    "vibe code",
    "vibe-code",
    "vibe coded",
    "vibe-coded",
    "vibe codes",
    "vibe-codes",
    "vibe coders",
    "vibe-coders",
    "vibecode",
    "vibe coder",
    "ngoding pakai ai",
    "kode pakai ai",
]
DEFAULT_OUTPUT_DIR = Path("data/raw")
DEFAULT_SESSION_PATH = Path("sessions/x_session.json")
DEFAULT_PROFILE_DIR = Path("sessions/x_profile")
X_HOME_URL = "https://x.com/home"
X_SEARCH_URL = "https://x.com/search?q={query}&src=typed_query&f=live"


@dataclass
class XPostRecord:
    collected_at: str
    date_window_start: str
    date_window_end: str
    search_query: str
    post_url: str | None
    username: str | None
    displayname: str | None
    created_at: str | None
    text: str
    reply_count: str | None
    repost_count: str | None
    like_count: str | None
    view_count: str | None


def build_date_windows(start_date: date, end_date: date, chunk_days: int) -> list[tuple[date, date]]:
    windows = []
    cursor = start_date
    while cursor < end_date:
        next_cursor = min(cursor + timedelta(days=chunk_days), end_date)
        windows.append((cursor, next_cursor))
        cursor = next_cursor
    return windows


def build_search_query(base_query: str, since: date, until: date) -> str:
    return f"({base_query}) since:{since.isoformat()} until:{until.isoformat()}"


def build_output_path(output: str | None) -> Path:
    if output:
        return Path(output)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"x_playwright_vibecoding_5y_{timestamp}.csv"


def normalize_count(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def clean_cell(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = value.replace("\r", " ").replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def clean_post_text(text: str, username: str | None, displayname: str | None) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_lines = []
    skip_next_reply_target = False

    for line in lines:
        if displayname and line == displayname:
            continue
        if username and line == f"@{username}":
            continue
        if line in {"·", "Tampilkan lebih banyak", "Show more", "Media tidak dapat dimainkan.", "Muat ulang"}:
            continue
        if re.fullmatch(r"\d{1,2}\s+\w+\s+\d{4}", line):
            continue
        if re.fullmatch(r"\d{1,2}-[A-Za-z]{3}-\d{2}", line):
            continue
        if re.fullmatch(r"\d+\s*(s|m|h|d|mnt|j|jam|hr|hari)", line, flags=re.IGNORECASE):
            continue
        if line == "Membalas":
            skip_next_reply_target = True
            continue
        if skip_next_reply_target and line.startswith("@"):
            skip_next_reply_target = False
            continue
        skip_next_reply_target = False
        cleaned_lines.append(line)

    return clean_cell(" ".join(cleaned_lines))


def parse_keywords(value: str | None) -> list[str]:
    if value is None:
        return DEFAULT_RELEVANT_KEYWORDS
    keywords = [keyword.strip().lower() for keyword in value.split(",")]
    return [keyword for keyword in keywords if keyword]


def is_relevant_text(text: str, keywords: list[str], strict_context: bool) -> bool:
    if strict_context and not is_core_vibe_coding_text(text):
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def is_core_vibe_coding_text(text: str) -> bool:
    lowered = text.lower()
    negative_patterns = [
        r"\$vibe\b",
        r"\bvibe\s+coded\s+(coin|token|meme|memecoin)\b",
        r"\b(coin|token|memecoin|airdrop|degen|solana|ethereum|eth|pump|bags?|holder|chart|kaito|vibescore)\b",
        r"\b(girl|rich girl|outfit|fashion|slay|yass|queen)\s+vibe\s+coded\b",
        r"\bvibe\s+coded\s+(bag|tweet)\b",
    ]
    if any(re.search(pattern, lowered) for pattern in negative_patterns):
        return False

    explicit_patterns = [
        r"\bvibe\s*[-]?\s*coding\b",
        r"\bvibecoding\b",
        r"\bngoding\s+pakai\s+ai\b",
        r"\bkode\s+pakai\s+ai\b",
    ]
    if any(re.search(pattern, lowered) for pattern in explicit_patterns):
        return True

    ambiguous_patterns = [
        r"\bvibe\s*[-]?\s*code(?:d|s|r|rs)?\b",
        r"\bvibecode(?:d|s|r|rs)?\b",
    ]
    if not any(re.search(pattern, lowered) for pattern in ambiguous_patterns):
        return False

    tech_context_patterns = [
        r"\b(ai|llm|agent|prompt|mcp|claude|gpt|cursor|windsurf|copilot|lovable|replit|bolt|v0)\b",
        r"\b(dev|developer|software|programming|program|debug|bug|git|github|repo|api|stack)\b",
        r"\b(app|website|webapp|product|startup|prototype|project|build|built|ship|shipped|launch|tool|platform)\b",
        r"\bfrontend|backend|fullstack|database|script|terminal|ide|pull request|pr\b",
    ]
    return any(re.search(pattern, lowered) for pattern in tech_context_patterns)


def extract_post_url(urls: list[str]) -> str | None:
    for url in urls:
        if re.search(r"/status/\d+", url):
            return url if url.startswith("http") else f"https://x.com{url}"
    return None


def load_playwright_cookies(cookies_path: str) -> list[dict[str, Any]]:
    path = Path(cookies_path)
    if not path.exists():
        raise FileNotFoundError(f"File cookies tidak ditemukan: {path}")

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    raw_cookies = raw_data.get("cookies", raw_data) if isinstance(raw_data, dict) else raw_data
    if not isinstance(raw_cookies, list):
        raise ValueError("Format cookies harus berupa list JSON atau object dengan key cookies.")

    cookies = []
    for raw_cookie in raw_cookies:
        if not isinstance(raw_cookie, dict) or "name" not in raw_cookie or "value" not in raw_cookie:
            continue

        cookie = {
            "name": str(raw_cookie["name"]),
            "value": str(raw_cookie["value"]),
            "domain": str(raw_cookie.get("domain") or ".x.com"),
            "path": str(raw_cookie.get("path") or "/"),
            "httpOnly": bool(raw_cookie.get("httpOnly", False)),
            "secure": bool(raw_cookie.get("secure", True)),
        }

        expires = raw_cookie.get("expires", raw_cookie.get("expirationDate"))
        if isinstance(expires, int | float) and expires > 0:
            cookie["expires"] = float(expires)

        same_site = raw_cookie.get("sameSite")
        if isinstance(same_site, str):
            same_site = same_site.lower()
            if same_site == "strict":
                cookie["sameSite"] = "Strict"
            elif same_site == "lax":
                cookie["sameSite"] = "Lax"
            elif same_site in {"none", "no_restriction"}:
                cookie["sameSite"] = "None"

        cookies.append(cookie)

    cookie_names = {cookie["name"] for cookie in cookies}
    if "auth_token" not in cookie_names:
        raise ValueError("Cookies tidak berisi auth_token.")
    if "ct0" not in cookie_names:
        raise ValueError("Cookies tidak berisi ct0.")

    return cookies


async def accept_possible_dialogs(page: Page) -> None:
    for label in ["Accept all cookies", "Accept cookies", "Got it", "Not now"]:
        try:
            button = page.get_by_text(label, exact=True).first
            if await button.count() > 0:
                await button.click(timeout=1500)
        except PlaywrightTimeoutError:
            pass
        except Exception:
            pass


async def launch_persistent_context(
    playwright: Any,
    profile_dir: Path,
    headless: bool,
    browser_channel: str,
) -> Any:
    profile_dir.mkdir(parents=True, exist_ok=True)
    launch_options = {
        "headless": headless,
        "viewport": {"width": 1366, "height": 768},
        "locale": "en-US",
    }

    if browser_channel != "bundled":
        launch_options["channel"] = browser_channel

    try:
        return await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            **launch_options,
        )
    except Exception:
        if browser_channel == "bundled":
            raise

        print(f"Gagal membuka browser channel '{browser_channel}', mencoba Chromium bawaan Playwright.")
        launch_options.pop("channel", None)
        return await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            **launch_options,
        )


async def save_manual_login_session(profile_dir: Path, headless: bool, browser_channel: str) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        context = await launch_persistent_context(
            playwright=playwright,
            profile_dir=profile_dir,
            headless=headless,
            browser_channel=browser_channel,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://x.com/login", wait_until="domcontentloaded")
        await accept_possible_dialogs(page)

        print("Browser login X sudah dibuka.")
        print("Silakan login manual sampai halaman X/home terbuka.")
        print("Jika login Google stuck, coba login X dengan username/email dan password langsung.")
        input("Setelah login berhasil, tekan ENTER di terminal ini untuk menyimpan session...")

        await context.close()

    print(f"Profile session tersimpan di: {profile_dir}")


async def import_cookies_to_profile(
    profile_dir: Path,
    cookies_path: str,
    headless: bool,
    browser_channel: str,
) -> None:
    async with async_playwright() as playwright:
        context = await launch_persistent_context(
            playwright=playwright,
            profile_dir=profile_dir,
            headless=headless,
            browser_channel=browser_channel,
        )
        await context.add_cookies(load_playwright_cookies(cookies_path))
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(X_HOME_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"Cookies berhasil di-import ke profile: {profile_dir}")
        print(f"Current URL: {page.url}")
        await context.close()


async def open_authenticated_page(
    profile_dir: Path,
    headless: bool,
    browser_channel: str,
    cookies_path: str | None,
) -> tuple[Any, Any, Page]:
    if not profile_dir.exists() and not cookies_path:
        raise FileNotFoundError(
            f"Profile session belum ada: {profile_dir}. Jalankan login manual dulu dengan --login atau --cookies."
        )

    playwright = await async_playwright().start()
    context = await launch_persistent_context(
        playwright=playwright,
        profile_dir=profile_dir,
        headless=headless,
        browser_channel=browser_channel,
    )
    if cookies_path:
        await context.add_cookies(load_playwright_cookies(cookies_path))

    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(X_HOME_URL, wait_until="domcontentloaded")
    await accept_possible_dialogs(page)
    return playwright, context, page


async def auto_scroll(page: Page, scrolls: int, delay_ms: int) -> None:
    for _ in range(scrolls):
        await page.mouse.wheel(0, 1800)
        await page.wait_for_timeout(delay_ms)


async def collect_visible_records(
    page: Page,
    search_query: str,
    since: date,
    until: date,
    relevant_keywords: list[str],
    strict_context: bool,
) -> list[dict[str, Any]]:
    articles = page.locator("article")
    count = await articles.count()
    records = []

    for index in range(count):
        record = await extract_post_from_article(articles.nth(index), search_query, since, until)
        if record is not None and is_relevant_text(record.text, relevant_keywords, strict_context):
            records.append(asdict(record))

    return records


async def extract_post_from_article(article: Any, search_query: str, since: date, until: date) -> XPostRecord | None:
    try:
        text = await article.inner_text(timeout=3000)
    except PlaywrightTimeoutError:
        return None

    links = await article.locator("a").evaluate_all("els => els.map(e => e.getAttribute('href')).filter(Boolean)")
    post_url = extract_post_url(links)

    time_locator = article.locator("time").first
    created_at = None
    if await time_locator.count() > 0:
        created_at = await time_locator.get_attribute("datetime")

    username_match = re.search(r"@(\w+)", text)
    username = username_match.group(1) if username_match else None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    displayname = lines[0] if lines else None
    cleaned_text = clean_post_text(text, username, displayname)

    aria_labels = await article.locator("[aria-label]").evaluate_all("els => els.map(e => e.getAttribute('aria-label')).filter(Boolean)")
    metrics_text = " | ".join(aria_labels)

    return XPostRecord(
        collected_at=datetime.now(timezone.utc).isoformat(),
        date_window_start=since.isoformat(),
        date_window_end=until.isoformat(),
        search_query=search_query,
        post_url=post_url,
        username=username,
        displayname=displayname,
        created_at=created_at,
        text=cleaned_text,
        reply_count=normalize_count(extract_metric(metrics_text, "repl")),
        repost_count=normalize_count(extract_metric(metrics_text, "repost")),
        like_count=normalize_count(extract_metric(metrics_text, "like")),
        view_count=normalize_count(extract_metric(metrics_text, "view")),
    )


def extract_metric(metrics_text: str, keyword: str) -> str | None:
    pattern = rf"([\d,.]+\s*[KMB]?)\s+[^|]*{keyword}"
    match = re.search(pattern, metrics_text, flags=re.IGNORECASE)
    return match.group(1) if match else None


async def scrape_search_window(
    page: Page,
    base_query: str,
    since: date,
    until: date,
    scrolls: int,
    delay_ms: int,
    relevant_keywords: list[str],
    strict_context: bool,
) -> list[dict[str, Any]]:
    search_query = build_search_query(base_query, since, until)
    search_url = X_SEARCH_URL.format(query=quote(search_query))

    print(f"Scraping {since.isoformat()} -> {until.isoformat()}")
    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(delay_ms)
    records_by_url = {}

    for _ in range(scrolls + 1):
        records = await collect_visible_records(page, search_query, since, until, relevant_keywords, strict_context)
        for record in records:
            key = record.get("post_url") or f"{record.get('username')}:{record.get('created_at')}:{record.get('text')}"
            records_by_url[key] = record
        await page.mouse.wheel(0, 1800)
        await page.wait_for_timeout(delay_ms)

    print(f"Collected {len(records_by_url)} relevant posts")
    return list(records_by_url.values())


async def scrape_five_years(
    profile_dir: Path,
    base_queries: list[str],
    chunk_days: int,
    scrolls_per_window: int,
    delay_ms: int,
    headless: bool,
    browser_channel: str,
    cookies_path: str | None,
    relevant_keywords: list[str],
    max_windows: int | None,
    target_rows: int | None,
    strict_context: bool,
) -> pd.DataFrame:
    end_date = datetime.now(timezone.utc).date() + timedelta(days=1)
    start_date = end_date - timedelta(days=365 * 5)
    windows = build_date_windows(start_date, end_date, chunk_days)
    if max_windows is not None:
        windows = windows[-max_windows:]
    if target_rows is not None:
        windows = list(reversed(windows))

    playwright, context, page = await open_authenticated_page(
        profile_dir=profile_dir,
        headless=headless,
        browser_channel=browser_channel,
        cookies_path=cookies_path,
    )
    all_records = []
    seen_keys = set()
    target_reached = False

    try:
        for query_index, base_query in enumerate(base_queries, start=1):
            print(f"=== Query {query_index}/{len(base_queries)}: {base_query} ===")
            for since, until in windows:
                records = await scrape_search_window(
                    page=page,
                    base_query=base_query,
                    since=since,
                    until=until,
                    scrolls=scrolls_per_window,
                    delay_ms=delay_ms,
                    relevant_keywords=relevant_keywords,
                    strict_context=strict_context,
                )
                for record in records:
                    key = record.get("post_url") or f"{record.get('username')}:{record.get('created_at')}:{record.get('text')}"
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    all_records.append(record)

                print(f"Total unique rows so far: {len(all_records)}")
                if target_rows is not None and len(all_records) >= target_rows:
                    all_records = all_records[:target_rows]
                    print(f"Target rows reached: {target_rows}")
                    target_reached = True
                    break
            if target_reached:
                break
    finally:
        await context.close()
        await playwright.stop()

    df = pd.DataFrame(all_records)
    if not df.empty and "post_url" in df.columns:
        df = df.drop_duplicates(subset=["post_url"]).reset_index(drop=True)
    return df


def save_csv(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = df.map(clean_cell) if not df.empty else df
    df.to_csv(output_path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape X search results with Playwright manual login session.")
    parser.add_argument("--login", action="store_true", help="Open browser for manual X login and save session.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Base X search query without since/until filters.")
    parser.add_argument("--queries", default=None, help="Semicolon-separated list of base queries to scrape and merge with global dedupe.")
    parser.add_argument("--use-query-variants", action="store_true", help="Use built-in vibe coding query variants for broader relevant coverage.")
    parser.add_argument("--session", default=str(DEFAULT_SESSION_PATH), help="Legacy session JSON path.")
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE_DIR), help="Persistent browser profile directory.")
    parser.add_argument("--browser-channel", default="msedge", choices=["msedge", "chrome", "bundled"], help="Browser channel for login and scraping.")
    parser.add_argument("--cookies", default=None, help="Path to exported x.com cookies JSON.")
    parser.add_argument("--import-cookies-only", action="store_true", help="Only import cookies into the Playwright profile, then exit.")
    parser.add_argument("--relevant-keywords", default=None, help="Comma-separated keywords used to keep only relevant posts.")
    parser.add_argument("--max-windows", type=int, default=None, help="Only scrape the latest N date windows.")
    parser.add_argument("--target-rows", type=int, default=None, help="Stop after collecting this many unique rows.")
    parser.add_argument("--no-strict-context", action="store_true", help="Disable strict vibe-coding phrase filter.")
    parser.add_argument("--chunk-days", type=int, default=30, help="Date window size in days for the 5-year scrape.")
    parser.add_argument("--scrolls-per-window", type=int, default=5, help="Number of scrolls per date window.")
    parser.add_argument("--delay-ms", type=int, default=2500, help="Delay after navigation/scroll in milliseconds.")
    parser.add_argument("--output", default=None, help="Output CSV path.")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode after session exists.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    profile_dir = Path(args.profile_dir)

    if args.login:
        await save_manual_login_session(
            profile_dir=profile_dir,
            headless=False,
            browser_channel=args.browser_channel,
        )
        return

    if args.import_cookies_only:
        if not args.cookies:
            raise ValueError("Argumen --cookies wajib diisi untuk --import-cookies-only.")
        await import_cookies_to_profile(
            profile_dir=profile_dir,
            cookies_path=args.cookies,
            headless=args.headless,
            browser_channel=args.browser_channel,
        )
        return

    if args.use_query_variants:
        base_queries = list(DEFAULT_QUERY_VARIANTS)
    elif args.queries:
        base_queries = [q.strip() for q in args.queries.split(";") if q.strip()]
    else:
        base_queries = [args.query]

    df = await scrape_five_years(
        profile_dir=profile_dir,
        base_queries=base_queries,
        chunk_days=args.chunk_days,
        scrolls_per_window=args.scrolls_per_window,
        delay_ms=args.delay_ms,
        headless=args.headless,
        browser_channel=args.browser_channel,
        cookies_path=args.cookies,
        relevant_keywords=parse_keywords(args.relevant_keywords),
        max_windows=args.max_windows,
        target_rows=args.target_rows,
        strict_context=not args.no_strict_context,
    )
    output_path = save_csv(df, build_output_path(args.output))

    print(f"Total rows after dedupe: {len(df)}")
    print(f"CSV saved to: {output_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}")
        raise SystemExit(1)
