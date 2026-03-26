import os
import sqlite3
from functools import wraps

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "database", "expense_tracker.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["DATABASE"] = DB_FILE


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        # turn on foreign keys
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db_connection(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            connection.executescript(schema_file.read())


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        # check if logged in
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapper


def add_expense(user_id, amount, category, expense_date, description):
    db = get_db()
    db.execute(
        """
        INSERT INTO expenses (user_id, amount, category, expense_date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, category, expense_date, description),
    )
    db.commit()


def get_expenses(user_id, category=None):
    db = get_db()
    if category:
        query = """
            SELECT id, amount, category, expense_date, description
            FROM expenses
            WHERE user_id = ? AND category = ?
            ORDER BY expense_date DESC, id DESC
        """
        params = (user_id, category)
    else:
        query = """
            SELECT id, amount, category, expense_date, description
            FROM expenses
            WHERE user_id = ?
            ORDER BY expense_date DESC, id DESC
        """
        params = (user_id,)
    return db.execute(query, params).fetchall()


def calculate_total(user_id, category=None):
    # let sqlite sum it
    db = get_db()
    if category:
        result = db.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = ? AND category = ?
            """,
            (user_id, category),
        ).fetchone()
    else:
        result = db.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return result["total"]


def get_categories(user_id):
    db = get_db()
    rows = db.execute(
        """
        SELECT DISTINCT category
        FROM expenses
        WHERE user_id = ?
        ORDER BY category ASC
        """,
        (user_id,),
    ).fetchall()
    return [row["category"] for row in rows]


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not username or not password:
            flash("Username and password are required.", "error")
        elif existing:
            flash("That username is already taken.", "error")
        else:
            password_hash = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            db.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        db = get_db()
        user = db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    selected_category = request.args.get("category", "").strip()
    expenses = get_expenses(session["user_id"], selected_category or None)
    total = calculate_total(session["user_id"], selected_category or None)
    cats = get_categories(session["user_id"])

    return render_template(
        "dashboard.html",
        expenses=expenses,
        total=total,
        categories=cats,
        selected_category=selected_category,
    )


@app.route("/expenses/add", methods=["POST"])
@login_required
def create_expense():
    amount_text = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    expense_date = request.form.get("expense_date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_text)
    except ValueError:
        amount = -1

    if amount <= 0 or not category or not expense_date:
        flash("Amount, category, and date are required.", "error")
    else:
        add_expense(session["user_id"], amount, category, expense_date, description)
        flash("Expense added.", "success")

    return redirect(url_for("dashboard"))


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(expense_id):
    db = get_db()
    # only delete your own row
    db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, session["user_id"]),
    )
    db.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    # make tables on first run
    init_db()
    app.run(debug=True)
