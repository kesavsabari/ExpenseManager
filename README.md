# Personal Expense Tracker

A simple Flask + SQLite web app to manage personal expenses.

## Stack
- Python
- Flask
- SQLite
- HTML (Jinja2)
- CSS

## Features
- Register, login, logout
- Add and delete expenses
- View all expenses
- Filter by category
- Sort by latest date
- Show total spending

## Project Structure

app.py
database/schema.sql
templates/ (HTML files)
static/style.css
requirements.txt

## How It Works
- Users log in and manage their own expenses
- Each expense includes amount, category, date, and description
- Expenses are stored in SQLite
- Data is filtered, sorted, and total is calculated using SQL

## How To Run
1. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2. Run the app:

```powershell
python app.py
```

3. Open:

```text
http://127.0.0.1:5000
```

## Notes
- Database is created automatically
