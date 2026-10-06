from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import sqlite3
import os
import html


BASE_DIR = "/root/main"

DB_PATH = os.path.join(
    BASE_DIR,
    "college-football",
    "college_football.db"
)

INDEX_PATH = os.path.join(
    BASE_DIR,
    "index.html"
)

COLLEGE_HTML_PATH = os.path.join(
    BASE_DIR,
    "college-football",
    "college_football.html"
)

GAME_HTML_PATH = os.path.join(
    BASE_DIR,
    "college-football",
    "game.html"
)


# -----------------------------
# FILE HELPERS
# -----------------------------

def load_html(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# Loads an HTML template from disk.


def safe(value):
    if value is None:
        return ""

    return html.escape(str(value))


# Prevents database text from becoming executable HTML.


def format_line(line):
    if line is None:
        return ""

    number = float(line)

    if number > 0:
        return f"+{number:g}"

    return f"{number:g}"


# Displays spread lines like +3.5 instead of 3.5.


# -----------------------------
# DATABASE QUERIES
# -----------------------------

def get_games():
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute("""
        SELECT
            g.id,
            g.away_team,
            g.home_team,
            g.game_date,
            g.status,
            COUNT(b.id) AS observation_count
        FROM games g

        LEFT JOIN bet_observations b
            ON b.game_id = g.id

        GROUP BY
            g.id,
            g.away_team,
            g.home_team,
            g.game_date,
            g.status

        ORDER BY g.game_date ASC
    """).fetchall()

    conn.close()

    return rows


# Returns every game with its total observation count.


def get_game(game_id):
    conn = sqlite3.connect(DB_PATH)

    row = conn.execute("""
        SELECT
            id,
            away_team,
            home_team,
            game_date,
            status
        FROM games
        WHERE id = ?
    """, (game_id,)).fetchone()

    conn.close()

    return row


# Returns basic information about one game.


def get_game_consensus(game_id):
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute("""
        SELECT
            market_type,
            selection,
            line,

            COUNT(*) AS observation_count,

            SUM(
                CASE
                    WHEN explicit_pick = 1 THEN 1
                    ELSE 0
                END
            ) AS explicit_count,

            ROUND(
                AVG(extraction_confidence),
                2
            ) AS avg_confidence

        FROM bet_observations

        WHERE game_id = ?
          AND stance = 'supports'

        GROUP BY
            market_type,
            selection,
            line

        ORDER BY
            market_type,
            observation_count DESC
    """, (game_id,)).fetchall()

    conn.close()

    return rows


# Groups matching supported bets into consensus rows.


# -----------------------------
# CONSENSUS LOGIC
# -----------------------------

def build_consensus(rows):
    markets = {}

    for row in rows:
        (
            market,
            selection,
            line,
            observation_count,
            explicit_count,
            avg_confidence
        ) = row

        markets.setdefault(market, [])

        markets[market].append({
            "selection": selection,
            "line": line,
            "count": observation_count,
            "explicit": explicit_count,
            "confidence": avg_confidence,
        })

    for market, bets in markets.items():

        total = sum(
            bet["count"]
            for bet in bets
        )

        for bet in bets:

            if total:
                bet["percentage"] = round(
                    bet["count"] / total * 100
                )
            else:
                bet["percentage"] = 0

        bets.sort(
            key=lambda bet: bet["count"],
            reverse=True
        )

    return markets


# Calculates support percentages within each market.


def get_game_leaders(game_id):
    consensus = build_consensus(
        get_game_consensus(game_id)
    )

    leaders = {}

    for market, bets in consensus.items():

        if bets:
            leaders[market] = bets[0]

    return leaders


# Returns the most-supported bet from each market.


def market_label(market):
    labels = {
        "spread": "Spread",
        "moneyline": "Moneyline",
        "total": "Total",
        "team_total": "Team Total",
        "player_prop": "Player Props",
        "other": "Other",
    }

    return labels.get(
        market,
        market.replace("_", " ").title()
    )


# Converts database market names into readable labels.


# -----------------------------
# COLLEGE FOOTBALL OVERVIEW
# -----------------------------

def build_game_cards():
    games = get_games()

    if not games:
        return """
        <div class="empty-state">
            No games stored yet.
        </div>
        """

    cards = ""

    for game in games:

        (
            game_id,
            away,
            home,
            game_date,
            status,
            observation_count
        ) = game

        leaders = get_game_leaders(game_id)

        summary_rows = ""

        market_order = [
            "spread",
            "moneyline",
            "total",
            "team_total",
            "player_prop",
        ]

        ordered_markets = []

        for market in market_order:
            if market in leaders:
                ordered_markets.append(market)

        for market in leaders:
            if market not in ordered_markets:
                ordered_markets.append(market)

        for market in ordered_markets:

            bet = leaders[market]

            line_text = format_line(
                bet["line"]
            )

            bet_text = safe(
                bet["selection"]
            )

            if line_text:
                bet_text += f" {line_text}"

            summary_rows += f"""
            <div class="summary-row">

                <div class="market-name">
                    {safe(market_label(market))}
                </div>

                <div class="bet-name">
                    {bet_text}
                </div>

                <div class="support">
                    {bet["percentage"]}%
                </div>

            </div>
            """

        if not summary_rows:
            summary_rows = """
            <div class="no-bets">
                No supported bets yet.
            </div>
            """

        cards += f"""
        <a
            class="game-card"
            href="/college-football/game?id={game_id}"
        >

            <div class="game-header">

                <div>
                    <h2>
                        {safe(away)} @ {safe(home)}
                    </h2>

                    <div class="game-date">
                        {safe(game_date)}
                    </div>
                </div>

                <div class="game-meta">
                    {observation_count} observations
                </div>

            </div>

            <div class="consensus-preview">
                {summary_rows}
            </div>

        </a>
        """

    return cards


# Builds compact cards for the main football page.


def render_college_football():
    template = load_html(
        COLLEGE_HTML_PATH
    )

    game_cards = build_game_cards()

    return template.replace(
        "{{GAME_CARDS}}",
        game_cards
    )


# Inserts generated game cards into college_football.html.


# -----------------------------
# INDIVIDUAL GAME PAGE
# -----------------------------

def build_consensus_tables(game_id):
    consensus = build_consensus(
        get_game_consensus(game_id)
    )

    if not consensus:
        return """
        <div class="empty-state">
            No betting observations for this game yet.
        </div>
        """

    market_order = [
        "spread",
        "moneyline",
        "total",
        "team_total",
        "player_prop",
    ]

    ordered_markets = []

    for market in market_order:
        if market in consensus:
            ordered_markets.append(market)

    for market in consensus:
        if market not in ordered_markets:
            ordered_markets.append(market)

    output = ""

    for market in ordered_markets:

        bets = consensus[market]

        rows = ""

        for index, bet in enumerate(bets):

            line_text = format_line(
                bet["line"]
            )

            selection = safe(
                bet["selection"]
            )

            if line_text:
                selection += f" {line_text}"

            leader_class = (
                " leader"
                if index == 0
                else ""
            )

            confidence = (
                bet["confidence"]
                if bet["confidence"] is not None
                else "N/A"
            )

            rows += f"""
            <tr class="{leader_class}">

                <td>
                    {selection}
                </td>

                <td>
                    {bet["count"]}
                </td>

                <td>
                    {bet["percentage"]}%
                </td>

                <td>
                    {bet["explicit"]}
                </td>

                <td>
                    {confidence}
                </td>

            </tr>
            """

        output += f"""
        <section class="market-card">

            <div class="market-header">

                <h2>
                    {safe(market_label(market))}
                </h2>

                <span>
                    {sum(b["count"] for b in bets)}
                    observations
                </span>

            </div>

            <table>

                <thead>
                    <tr>
                        <th>Bet</th>
                        <th>Obs.</th>
                        <th>Support</th>
                        <th>Explicit</th>
                        <th>Extract Conf.</th>
                    </tr>
                </thead>

                <tbody>
                    {rows}
                </tbody>

            </table>

        </section>
        """

    return output


# Builds compact consensus tables instead of observation cards.


def render_game(game_id):
    game = get_game(game_id)

    if not game:
        return None

    (
        game_id,
        away,
        home,
        game_date,
        status
    ) = game

    template = load_html(
        GAME_HTML_PATH
    )

    consensus_tables = build_consensus_tables(
        game_id
    )

    replacements = {
        "{{AWAY_TEAM}}": safe(away),
        "{{HOME_TEAM}}": safe(home),
        "{{GAME_DATE}}": safe(game_date),
        "{{STATUS}}": safe(status),
        "{{CONSENSUS_TABLES}}": consensus_tables,
    }

    for placeholder, value in replacements.items():
        template = template.replace(
            placeholder,
            value
        )

    return template


# Inserts game information into game.html.


# -----------------------------
# HTTP SERVER
# -----------------------------

class Handler(BaseHTTPRequestHandler):

    def send_html(self, content, status=200):
        encoded = content.encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(encoded))
        )

        self.end_headers()

        self.wfile.write(encoded)


    def do_GET(self):
        parsed = urlparse(
            self.path
        )

        path = parsed.path

        query = parse_qs(
            parsed.query
        )

        if path == "/":

            try:
                content = load_html(
                    INDEX_PATH
                )

            except FileNotFoundError:
                self.send_html(
                    "<h1>index.html not found</h1>",
                    500
                )

                return

            self.send_html(content)
            return


        if path == "/college-football":

            try:
                content = render_college_football()

            except Exception as error:
                print(
                    "College football page error:",
                    error
                )

                self.send_html(
                    "<h1>Unable to load college football page.</h1>",
                    500
                )

                return

            self.send_html(content)
            return


        if path == "/college-football/game":

            try:
                game_id = int(
                    query["id"][0]
                )

            except (
                KeyError,
                IndexError,
                ValueError
            ):
                self.send_html(
                    "<h1>Invalid game ID.</h1>",
                    400
                )

                return

            try:
                content = render_game(
                    game_id
                )

            except Exception as error:
                print(
                    "Game page error:",
                    error
                )

                self.send_html(
                    "<h1>Unable to load game.</h1>",
                    500
                )

                return

            if content is None:

                self.send_html(
                    "<h1>Game not found.</h1>",
                    404
                )

                return

            self.send_html(content)
            return


        self.send_html(
            "<h1>404 - Page not found</h1>",
            404
        )


server = HTTPServer(
    ("127.0.0.1", 8000),
    Handler
)

print(
    "Server running on http://127.0.0.1:8000"
)

server.serve_forever()