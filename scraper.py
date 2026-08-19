import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import shutil
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from twscrape import API
from twscrape.utils import parse_cookies


DEFAULT_QUERY = '(vibecoding OR "vibe coding" OR "AI coding" OR "ngoding pakai AI" OR "kode pakai AI")'
DEFAULT_OUTPUT_DIR = Path("data/raw")


def patch_twscrape_xclid_authenticated_client() -> None:
    import httpx
    from twscrape import queue_client

    if getattr(queue_client.Ctx.req, "_vibecoding_patched", False):
        return

    async def req(self: Any, method: str, url: str, params: Any = None) -> Any:
        path = urlparse(url).path or "/"
        tries = 0
        while tries < 3:
            fresh = tries > 0 or self.acc.username not in queue_client.XClIdGenStore.items
            headers = {}
            if fresh:
                try:
                    async with httpx.AsyncClient(
                        headers={"user-agent": self.acc.user_agent},
                        cookies=self.acc.cookies,
                        follow_redirects=True,
                    ) as xclid_client:
                        gen = await queue_client.XClIdGen.create(clt=xclid_client)
                    queue_client.XClIdGenStore.items[self.acc.username] = gen
                    headers = {"x-client-transaction-id": gen.calc(method, path)}
                except Exception as error:
                    queue_client.logger.warning(f"Skip x-client-transaction-id generation: {type(error).__name__}: {error}")
            else:
                gen = queue_client.XClIdGenStore.items[self.acc.username]
                headers = {"x-client-transaction-id": gen.calc(method, path)}

            response = await self.clt.request(method, url, params=params, headers=headers)
            if response.status_code != 404:
                return response

            tries += 1
            queue_client.logger.debug(f"Retrying request with new x-client-transaction-id: {url}")
            await asyncio.sleep(1)

        raise queue_client.AbortReqError(
            "Failed to get XClIdGen with authenticated client. Run twscrape reset_locks, refresh cookies, then try again."
        )

    setattr(req, "_vibecoding_patched", True)
    queue_client.Ctx.req = req


@dataclass
class TweetRecord:
    tweet_id: int | str | None
    created_at: str | None
    text: str
    author_id: int | str | None
    username: str | None
    displayname: str | None
    lang: str | None
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    view_count: int | None
    url: str | None
    search_query: str
    since: str
    until: str


def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    return getattr(obj, attr, default)


def tweet_to_record(tweet: Any, search_query: str, since: str, until: str) -> TweetRecord:
    user = safe_get(tweet, "user")
    return TweetRecord(
        tweet_id=safe_get(tweet, "id"),
        created_at=str(safe_get(tweet, "date")) if safe_get(tweet, "date") else None,
        text=safe_get(tweet, "rawContent", "") or safe_get(tweet, "renderedContent", ""),
        author_id=safe_get(user, "id") if user else None,
        username=safe_get(user, "username") if user else None,
        displayname=safe_get(user, "displayname") if user else None,
        lang=safe_get(tweet, "lang"),
        like_count=safe_get(tweet, "likeCount", 0) or 0,
        retweet_count=safe_get(tweet, "retweetCount", 0) or 0,
        reply_count=safe_get(tweet, "replyCount", 0) or 0,
        quote_count=safe_get(tweet, "quoteCount", 0) or 0,
        view_count=safe_get(tweet, "viewCount"),
        url=safe_get(tweet, "url"),
        search_query=search_query,
        since=since,
        until=until,
    )


def find_twscrape_command() -> str:
    local_command = Path(sys.executable).parent / "twscrape.exe"
    if local_command.exists():
        return str(local_command)

    twscrape_cmd = shutil.which("twscrape")
    if twscrape_cmd is None:
        raise FileNotFoundError("Command twscrape tidak ditemukan. Pastikan dependency sudah terinstall.")
    return twscrape_cmd


def run_twscrape(args: list[str]) -> int:
    command = [find_twscrape_command(), *args]
    return subprocess.run(command, check=False).returncode


def twscrape_output(args: list[str]) -> str:
    command = [find_twscrape_command(), *args]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    return f"{completed.stdout}\n{completed.stderr}".strip()


def load_browser_cookies(cookies_path: str) -> str:
    path = Path(cookies_path)
    if not path.exists():
        raise FileNotFoundError(f"File cookies tidak ditemukan: {path}")

    raw_cookies = path.read_text(encoding="utf-8").strip()
    if not raw_cookies:
        raise ValueError(f"File cookies kosong: {path}")

    try:
        parsed = json.loads(raw_cookies)
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    except json.JSONDecodeError:
        return raw_cookies


def ensure_active_accounts() -> None:
    output = twscrape_output(["accounts"])
    has_active_account = False
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] in {"0", "1"} and parts[2] == "1":
            has_active_account = True
            break

    if "No accounts" in output or "No active accounts" in output or not output or not has_active_account:
        raise RuntimeError(
            "Belum ada akun twscrape yang aktif. Jalankan login terlebih dahulu:\n"
            "  .\\.venv\\Scripts\\python.exe scraper.py --login-only --username USERNAME_ANDA --email EMAIL_ANDA\n"
            "Atau inject cookies browser yang sudah login:\n"
            "  .\\.venv\\Scripts\\python.exe scraper.py --inject-cookies-only --username USERNAME_ANDA --cookies cookies_x.json\n"
            "Setelah login berhasil, jalankan scraping lagi."
        )


async def inject_browser_cookies(
    username: str,
    cookies_path: str,
    password: str | None,
    email: str | None,
    email_password: str | None,
) -> None:
    cookies_value = load_browser_cookies(cookies_path)
    parsed_cookies = parse_cookies(cookies_value)

    if "ct0" not in parsed_cookies:
        raise ValueError("Cookies tidak berisi ct0. Export cookies dari browser yang sudah login ke x.com.")

    if "auth_token" not in parsed_cookies:
        raise ValueError("Cookies tidak berisi auth_token. Export cookies dari browser yang sudah login ke x.com.")

    api = API()
    account = await api.pool.get_account(username)

    if account is None:
        await api.pool.add_account(
            username=username,
            password=password or "",
            email=email or "",
            email_password=email_password or "",
            cookies=cookies_value,
        )
    else:
        account.password = password if password is not None else account.password
        account.email = email if email is not None else account.email
        account.email_password = email_password if email_password is not None else account.email_password
        account.cookies = parsed_cookies
        account.active = True
        account.error_msg = None
        await api.pool.save(account)

    await api.pool.set_active(username, True)
    print(f"Cookies berhasil di-inject untuk akun: {username}")
    run_twscrape(["accounts"])


def login_with_account_credentials(username: str, password: str, email: str, email_password: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as file:
        accounts_path = Path(file.name)
        file.write(f"{username}:{password}:{email}:{email_password}\n")

    try:
        add_code = run_twscrape(["add_accounts", str(accounts_path), "username:password:email:email_password"])
        if add_code != 0:
            raise RuntimeError(
                "Gagal menambahkan akun. Pastikan username, password, email, dan email password/app password benar."
            )

        login_code = run_twscrape(["login_accounts"])
        if login_code != 0:
            raise RuntimeError(
                "Gagal login akun. Cek username/password, status akun X, captcha, 2FA, atau security challenge."
            )

        run_twscrape(["accounts"])
    finally:
        accounts_path.unlink(missing_ok=True)


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


async def scrape_window(api: API, base_query: str, since: date, until: date, limit: int) -> list[dict[str, Any]]:
    dated_query = build_search_query(base_query, since, until)
    records = []

    print(f"Scraping {since.isoformat()} -> {until.isoformat()} | limit={limit}")
    async for tweet in api.search(dated_query, limit=limit):
        records.append(asdict(tweet_to_record(tweet, dated_query, since.isoformat(), until.isoformat())))

    print(f"Collected {len(records)} rows")
    return records


async def scrape_five_years(base_query: str, limit_per_window: int, chunk_days: int) -> pd.DataFrame:
    ensure_active_accounts()
    patch_twscrape_xclid_authenticated_client()

    api = API()
    end_date = datetime.now(timezone.utc).date() + timedelta(days=1)
    start_date = end_date - timedelta(days=365 * 5)
    windows = build_date_windows(start_date, end_date, chunk_days)

    all_records = []
    for since, until in windows:
        window_records = await scrape_window(api, base_query, since, until, limit_per_window)
        all_records.extend(window_records)

    df = pd.DataFrame(all_records)
    if not df.empty and "tweet_id" in df.columns:
        df = df.drop_duplicates(subset=["tweet_id"]).reset_index(drop=True)
    return df


def build_output_path(output: str | None) -> Path:
    if output:
        return Path(output)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"tweets_vibecoding_5y_{timestamp}.csv"


def save_csv(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape X data for the last five years using twscrape.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Base X search query without since/until filters.")
    parser.add_argument("--username", default=None, help="X username for login.")
    parser.add_argument("--password", default=None, help="X password. If omitted, it will be requested securely.")
    parser.add_argument("--email", default=None, help="Email connected to the X account.")
    parser.add_argument("--email-password", default=None, help="Email password or app password. If omitted, it will be requested securely.")
    parser.add_argument("--cookies", default=None, help="Path to exported browser cookies JSON/text from a logged-in X session.")
    parser.add_argument("--login", action="store_true", help="Login with X account credentials before scraping.")
    parser.add_argument("--login-only", action="store_true", help="Only login, then exit without scraping.")
    parser.add_argument("--inject-cookies", action="store_true", help="Inject exported browser cookies into a twscrape account before scraping.")
    parser.add_argument("--inject-cookies-only", action="store_true", help="Only inject exported browser cookies, then exit without scraping.")
    parser.add_argument("--limit-per-window", type=int, default=100, help="Maximum tweets per date window.")
    parser.add_argument("--chunk-days", type=int, default=30, help="Date window size in days for the 5-year scrape.")
    parser.add_argument("--output", default=None, help="Output CSV path. Default: data/raw/tweets_vibecoding_5y_YYYYMMDD_HHMMSS.csv")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.inject_cookies or args.inject_cookies_only:
        username = args.username or input("X username: ").strip()
        if not args.cookies:
            raise ValueError("Argumen --cookies wajib diisi untuk inject cookies.")

        await inject_browser_cookies(
            username=username,
            cookies_path=args.cookies,
            password=args.password,
            email=args.email,
            email_password=args.email_password,
        )

    if args.inject_cookies_only:
        return

    if args.login or args.login_only:
        username = args.username or input("X username: ").strip()
        password = args.password or getpass("X password: ")
        email = args.email or input("Email akun X: ").strip()
        email_password = args.email_password or getpass("Email password/app password: ")
        login_with_account_credentials(username, password, email, email_password)

    if args.login_only:
        return

    df = await scrape_five_years(
        base_query=args.query,
        limit_per_window=args.limit_per_window,
        chunk_days=args.chunk_days,
    )
    output_path = save_csv(df, build_output_path(args.output))

    print(f"Total rows after dedupe: {len(df)}")
    print(f"CSV saved to: {output_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
