from fastmcp import FastMCP
import sqlite3
import aiosqlite
import json
from pathlib import Path

# Project directory
BASE_DIR = Path(__file__).resolve().parent

# Database and categories
DB_PATH = BASE_DIR / "expenses.db"
CATEGORIES_PATH = BASE_DIR / "categories.json"

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")


def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
            conn.commit()

        print(f"Database initialized successfully: {DB_PATH}")

    except Exception as e:
        print(f"Database initialization error: {e}")
        raise


init_db()


@mcp.tool()
async def add_expense(
    date,
    amount,
    category,
    subcategory="",
    note=""
):
    """Add a new expense entry to the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cur = await conn.execute(
                """
                INSERT INTO expenses
                (date, amount, category, subcategory, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, amount, category, subcategory, note)
            )

            expense_id = cur.lastrowid
            await conn.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense added successfully"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


@mcp.tool()
async def list_expenses(start_date, end_date):
    """List expense entries within an inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cur = await conn.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )

            rows = await cur.fetchall()
            columns = [description[0] for description in cur.description]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing expenses: {str(e)}"
        }


@mcp.tool()
async def summarize(start_date, end_date, category=None):
    """Summarize expenses by category within an inclusive date range."""
    try:
        query = """
            SELECT
                category,
                SUM(amount) AS total_amount,
                COUNT(*) AS count
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += """
            GROUP BY category
            ORDER BY total_amount DESC
        """

        async with aiosqlite.connect(DB_PATH) as conn:
            cur = await conn.execute(query, params)

            rows = await cur.fetchall()
            columns = [description[0] for description in cur.description]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error summarizing expenses: {str(e)}"
        }


@mcp.resource(
    "expense:///categories",
    mime_type="application/json"
)
def categories():
    """Return available expense categories."""

    default_categories = {
        "categories": [
            "Food & Dining",
            "Transportation",
            "Shopping",
            "Entertainment",
            "Bills & Utilities",
            "Healthcare",
            "Travel",
            "Education",
            "Business",
            "Other"
        ]
    }

    try:
        if CATEGORIES_PATH.exists():
            return CATEGORIES_PATH.read_text(
                encoding="utf-8"
            )

        return json.dumps(
            default_categories,
            indent=2
        )

    except Exception as e:
        return json.dumps({
            "error": f"Could not load categories: {str(e)}"
        })