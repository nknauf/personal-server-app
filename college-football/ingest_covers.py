import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DB_PATH = "college_football.db"

URL = "https://www.covers.com/sport/football/ncaaf/matchup/378123/picks"

GAME_ID = 1
SOURCE_NAME = "Covers"


def get_source_id(conn):
    row = conn.execute("SELECT id FROM sources WHERE name = ?",(SOURCE_NAME,)).fetchone()
    if not row:
        raise RuntimeError("Covers source is not registered.")
    return row[0]


def fetch_page(url): 
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text


def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "noscript"
    ]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return text


def save_article(conn, source_id, text):
    title = "Pittsburgh vs Virginia Tech - Covers Picks"

    conn.execute(
        """
        INSERT OR IGNORE INTO articles
        (
            source_id,
            title,
            url,
            published_at,
            article_text,
            processed
        )
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (
            source_id,
            title,
            URL,
            datetime.utcnow().isoformat(),
            text
        )
    )

    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    source_id = get_source_id(conn)
    html = fetch_page(URL)
    print("Downloaded page.")
    text = extract_text(html)
    print(f"Extracted {len(text)} characters.")
    save_article(
        conn,
        source_id,
        text
    )
    print("Saved Covers page to database.")
    conn.close()


if __name__ == "__main__":
    main()