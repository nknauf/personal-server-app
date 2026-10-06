import os
import json
import sqlite3
from openai import OpenAI


DB_PATH = "college_football.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not configured.")

# Change this if your article has another ID.
ARTICLE_ID = 1

# Cheap model intended for repeated structured extraction.
MODEL = "gpt-5.6-luna"
client = OpenAI()

OBSERVATION_SCHEMA = {
    "type": "object",
    "properties": {
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "market_type": {
                        "type": "string",
                        "enum": [
                            "spread",
                            "moneyline",
                            "total",
                            "team_total",
                            "player_prop",
                            "other"
                        ]
                    },

                    "selection": {
                        "type": "string"
                    },

                    "line": {
                        "type": ["number", "null"]
                    },

                    "odds": {
                        "type": ["integer", "null"]
                    },

                    "stance": {
                        "type": "string",
                        "enum": [
                            "supports",
                            "opposes",
                            "neutral"
                        ]
                    },

                    "explicit_pick": {
                        "type": "boolean"
                    },

                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },

                    "reasoning": {
                        "type": "string"
                    }
                },

                "required": [
                    "market_type",
                    "selection",
                    "line",
                    "odds",
                    "stance",
                    "explicit_pick",
                    "confidence",
                    "reasoning"
                ],

                "additionalProperties": False
            }
        }
    },

    "required": ["observations"],
    "additionalProperties": False
}


def load_article(conn, article_id):
    row = conn.execute(
        """
        SELECT
            articles.id,
            articles.game_id,
            articles.title,
            articles.article_text,
            games.home_team,
            games.away_team
        FROM articles
        JOIN games
            ON articles.game_id = games.id
        WHERE articles.id = ?
        """,
        (article_id,)
    ).fetchone()

    if not row:
        raise RuntimeError(
            f"Article {article_id} was not found or has no game."
        )

    return {
        "article_id": row[0],
        "game_id": row[1],
        "title": row[2],
        "text": row[3],
        "home_team": row[4],
        "away_team": row[5],
    }



def extract_observations(article):
    prompt = f"""
You are extracting betting analyst observations from one college football article.

Game:
{article['away_team']} at {article['home_team']}

Article title:
{article['title']}

Rules:
1. Only extract betting positions actually supported by the article.
2. Do not invent picks.
3. Separate different bets into separate observations.
4. If the article discusses a bet but does not support or oppose it, mark stance as neutral.
5. explicit_pick=true only when the author clearly recommends or personally selects the wager.
6. confidence measures confidence in YOUR EXTRACTION, not confidence that the bet will win.
7. If no meaningful betting position exists, return an empty observations array.
8. reasoning must be a short paraphrase, not a long quotation.
9. Preserve the line shown in the article when available.
10. Do not infer odds if they are not stated.

Article:

{article['text']}
"""

    response = client.responses.create(
        model=MODEL,

        input=prompt,

        text={
            "format": {
                "type": "json_schema",
                "name": "betting_observations",
                "schema": OBSERVATION_SCHEMA,
                "strict": True
            }
        }
    )

    return json.loads(response.output_text)


def save_observations(conn, article, data):
    observations = data["observations"]

    for obs in observations:

        direction = None

        if obs["market_type"] == "total":
            selection_lower = obs["selection"].lower()

            if "under" in selection_lower:
                direction = "UNDER"

            elif "over" in selection_lower:
                direction = "OVER"

        conn.execute(
            """
            INSERT INTO bet_observations
            (
                article_id,
                game_id,
                market_type,
                selection,
                line,
                odds,
                direction,
                confidence,
                reasoning,
                stance,
                explicit_pick,
                extraction_confidence,
                model_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            (
                article["article_id"],
                article["game_id"],
                obs["market_type"],
                obs["selection"],
                obs["line"],
                obs["odds"],
                direction,
                obs["confidence"],
                obs["reasoning"],
                obs["stance"],
                1 if obs["explicit_pick"] else 0,
                obs["confidence"],
                MODEL
            )
        )

    conn.execute(
        """
        UPDATE articles
        SET processed = 1
        WHERE id = ?
        """,
        (article["article_id"],)
    )

    conn.commit()

    return len(observations)


def main():
    conn = sqlite3.connect(DB_PATH)
    article = load_article(
        conn,
        ARTICLE_ID
    )
    print(
        f"Analyzing article {article['article_id']}: "
        f"{article['title']}"
    )
    data = extract_observations(article)
    print("\nExtracted observations:")
    print(
        json.dumps(
            data,
            indent=2
        )
    )
    count = save_observations(
        conn,
        article,
        data
    )
    print(
        f"\nSaved {count} observations."
    )
    conn.close()


if __name__ == "__main__":
    main()