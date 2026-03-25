"""
Vault - Receipt & Expense Tracker
Flask Backend (Python)
Run: pip install flask flask-cors && python app.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, date
import json

app = Flask(__name__)
CORS(app)  # Allow frontend to connect

# ─── In-memory data store (replace with SQLite/PostgreSQL for production) ───

expenses = [
    {"id": 1, "name": "Swiggy Order",        "category": "food",      "amount": 348,  "date": "2026-03-22", "receipt": False, "source": "manual"},
    {"id": 2, "name": "Metro Card Recharge", "category": "travel",    "amount": 200,  "date": "2026-03-21", "receipt": False, "source": "manual"},
    {"id": 3, "name": "Amazon — Headphones", "category": "shopping",  "amount": 1999, "date": "2026-03-20", "receipt": True,  "source": "amazon"},
    {"id": 4, "name": "Apollo Pharmacy",     "category": "health",    "amount": 530,  "date": "2026-03-19", "receipt": True,  "source": "manual"},
    {"id": 5, "name": "Airtel Recharge",     "category": "utilities", "amount": 599,  "date": "2026-03-18", "receipt": False, "source": "manual"},
    {"id": 6, "name": "Zomato",              "category": "food",      "amount": 425,  "date": "2026-03-17", "receipt": False, "source": "zomato"},
]

# Monthly budget limits per category (in INR)
budget_limits = {
    "food":      2000,
    "travel":    1500,
    "shopping":  3000,
    "health":    1000,
    "utilities": 1500,
    "other":     1000,
}

# Reward badges definition
BADGES = [
    {"id": "saver_bronze",  "title": "Smart Saver",    "desc": "Spent less than 50% of any category budget",  "icon": "🥉", "threshold": 0.50},
    {"id": "saver_silver",  "title": "Budget Hero",    "desc": "Spent less than 30% of any category budget",  "icon": "🥈", "threshold": 0.30},
    {"id": "saver_gold",    "title": "Money Master",   "desc": "Spent less than 10% of any category budget",  "icon": "🥇", "threshold": 0.10},
    {"id": "streak_week",   "title": "Week Warrior",   "desc": "Tracked expenses every day for 7 days",        "icon": "🔥", "threshold": None},
    {"id": "receipt_champ", "title": "Receipt Champ",  "desc": "Attached receipts to 80%+ of expenses",       "icon": "📎", "threshold": 0.80},
]

# Simulated connected integrations
integrations = {
    "swiggy":  {"name": "Swiggy",   "icon": "🧡", "color": "#fc8019", "connected": False, "last_sync": None, "pending_txns": 3},
    "zomato":  {"name": "Zomato",   "icon": "🔴", "color": "#e23744", "connected": True,  "last_sync": "2026-03-22", "pending_txns": 0},
    "amazon":  {"name": "Amazon",   "icon": "📦", "color": "#ff9900", "connected": True,  "last_sync": "2026-03-20", "pending_txns": 1},
    "flipkart":{"name": "Flipkart", "icon": "💙", "color": "#2874f0", "connected": False, "last_sync": None, "pending_txns": 2},
    "blinkit": {"name": "Blinkit",  "icon": "⚡", "color": "#f8e000", "connected": False, "last_sync": None, "pending_txns": 0},
    "uber":    {"name": "Uber",     "icon": "🚗", "color": "#000000", "connected": False, "last_sync": None, "pending_txns": 0},
}

next_id = 7  # auto-increment ID counter


# ─── Helper functions ─────────────────────────────────────────────────────────

def get_current_month():
    return date.today().strftime("%Y-%m")

def get_monthly_spending(month=None):
    if not month:
        month = get_current_month()
    totals = {cat: 0 for cat in budget_limits}
    for e in expenses:
        if e["date"].startswith(month):
            totals[e["category"]] = totals.get(e["category"], 0) + e["amount"]
    return totals

def calculate_rewards():
    """Calculate earned badges based on current spending vs limits."""
    earned = []
    month_spend = get_monthly_spending()
    
    # Check spending-based badges
    for cat, spent in month_spend.items():
        limit = budget_limits.get(cat, 0)
        if limit == 0:
            continue
        ratio = spent / limit
        for badge in BADGES:
            if badge["threshold"] and ratio <= badge["threshold"]:
                earned.append({
                    **badge,
                    "category": cat,
                    "detail": f"{cat.capitalize()} at {int(ratio*100)}% of ₹{limit} limit"
                })
                break  # only best badge per category

    # Receipt champion badge
    if expenses:
        receipt_pct = sum(1 for e in expenses if e["receipt"]) / len(expenses)
        if receipt_pct >= 0.80:
            earned.append({**BADGES[4], "category": "all", "detail": f"{int(receipt_pct*100)}% receipt coverage"})

    return earned


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    """Get all expenses, optionally filtered by month."""
    month = request.args.get("month", None)
    if month:
        filtered = [e for e in expenses if e["date"].startswith(month)]
    else:
        filtered = expenses
    return jsonify({"expenses": sorted(filtered, key=lambda x: x["date"], reverse=True)})


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    """Add a new expense."""
    global next_id
    data = request.get_json()

    required = ["name", "category", "amount", "date"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    new_expense = {
        "id":       next_id,
        "name":     data["name"],
        "category": data["category"],
        "amount":   float(data["amount"]),
        "date":     data["date"],
        "receipt":  data.get("receipt", False),
        "source":   data.get("source", "manual"),
    }
    expenses.insert(0, new_expense)
    next_id += 1

    # Check if this expense triggers a budget warning
    month_spend = get_monthly_spending()
    cat = new_expense["category"]
    limit = budget_limits.get(cat, 0)
    spent = month_spend.get(cat, 0)
    warning = None
    if limit > 0 and spent >= limit * 0.9:
        warning = f"⚠️ You've used {int(spent/limit*100)}% of your {cat} budget!"

    return jsonify({"expense": new_expense, "warning": warning}), 201


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    """Delete an expense by ID."""
    global expenses
    before = len(expenses)
    expenses = [e for e in expenses if e["id"] != expense_id]
    if len(expenses) == before:
        return jsonify({"error": "Expense not found"}), 404
    return jsonify({"message": "Deleted successfully"})


@app.route("/api/budget", methods=["GET"])
def get_budget():
    """Get budget limits and current spending for each category."""
    month_spend = get_monthly_spending()
    result = []
    for cat, limit in budget_limits.items():
        spent = month_spend.get(cat, 0)
        result.append({
            "category": cat,
            "limit":    limit,
            "spent":    spent,
            "remaining": max(0, limit - spent),
            "percent":  round(min(100, (spent / limit * 100)) if limit > 0 else 0, 1),
            "status":   "over" if spent > limit else "warning" if spent >= limit * 0.8 else "ok"
        })
    return jsonify({"budget": result, "month": get_current_month()})


@app.route("/api/budget", methods=["PUT"])
def update_budget():
    """Update budget limits."""
    data = request.get_json()
    for cat, limit in data.items():
        if cat in budget_limits:
            budget_limits[cat] = float(limit)
    return jsonify({"budget_limits": budget_limits})


@app.route("/api/rewards", methods=["GET"])
def get_rewards():
    """Get earned reward badges."""
    earned = calculate_rewards()
    month_spend = get_monthly_spending()
    total_limit = sum(budget_limits.values())
    total_spent = sum(month_spend.values())
    savings = max(0, total_limit - total_spent)
    return jsonify({
        "badges":       earned,
        "badge_count":  len(earned),
        "total_savings": savings,
        "savings_pct":  round((savings / total_limit * 100) if total_limit > 0 else 0, 1),
        "month":        get_current_month(),
    })


@app.route("/api/integrations", methods=["GET"])
def get_integrations():
    """Get all available app integrations and their connection status."""
    return jsonify({"integrations": integrations})


@app.route("/api/integrations/<app_id>/connect", methods=["POST"])
def connect_integration(app_id):
    """Simulate connecting an app integration."""
    if app_id not in integrations:
        return jsonify({"error": "Integration not found"}), 404
    integrations[app_id]["connected"] = True
    integrations[app_id]["last_sync"] = date.today().isoformat()
    
    # Simulate importing pending transactions
    pending = integrations[app_id].get("pending_txns", 0)
    return jsonify({
        "message": f"Connected to {integrations[app_id]['name']} successfully!",
        "pending_transactions": pending,
        "integration": integrations[app_id]
    })


@app.route("/api/integrations/<app_id>/sync", methods=["POST"])
def sync_integration(app_id):
    """Simulate syncing transactions from a connected app."""
    global next_id
    if app_id not in integrations or not integrations[app_id]["connected"]:
        return jsonify({"error": "Integration not connected"}), 400

    # Simulate fetched transactions
    simulated_txns = {
        "swiggy":  [{"name": "Swiggy — Burger King", "amount": 299, "category": "food"}],
        "amazon":  [{"name": "Amazon — USB Cable",   "amount": 349, "category": "shopping"}],
        "flipkart":[{"name": "Flipkart — Earbuds",   "amount": 799, "category": "shopping"}],
        "zomato":  [{"name": "Zomato — Pizza Hut",   "amount": 520, "category": "food"}],
    }
    imported = []
    for txn in simulated_txns.get(app_id, []):
        new_e = {**txn, "id": next_id, "date": date.today().isoformat(), "receipt": True, "source": app_id}
        expenses.insert(0, new_e)
        imported.append(new_e)
        next_id += 1

    integrations[app_id]["last_sync"] = date.today().isoformat()
    integrations[app_id]["pending_txns"] = 0
    return jsonify({"imported": imported, "count": len(imported)})


@app.route("/api/summary", methods=["GET"])
def get_summary():
    """Get full dashboard summary."""
    month_spend = get_monthly_spending()
    total_limit = sum(budget_limits.values())
    total_spent = sum(month_spend.values())
    rewards = calculate_rewards()
    
    # Category breakdown
    by_category = []
    for cat, limit in budget_limits.items():
        spent = month_spend.get(cat, 0)
        by_category.append({
            "category": cat,
            "spent":    spent,
            "limit":    limit,
            "percent":  round((spent / limit * 100) if limit > 0 else 0, 1)
        })

    return jsonify({
        "total_expenses":   len(expenses),
        "total_spent":      sum(e["amount"] for e in expenses),
        "month_spent":      total_spent,
        "month_limit":      total_limit,
        "month_savings":    max(0, total_limit - total_spent),
        "badge_count":      len(rewards),
        "by_category":      by_category,
        "month":            get_current_month(),
    })


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export expenses as CSV."""
    from flask import Response
    lines = ["Date,Name,Category,Amount (INR),Has Receipt,Source"]
    for e in sorted(expenses, key=lambda x: x["date"], reverse=True):
        lines.append(f"{e['date']},\"{e['name']}\",{e['category']},{e['amount']},{('Yes' if e['receipt'] else 'No')},{e['source']}")
    csv_data = "\n".join(lines)
    return Response(csv_data, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=vault-expenses.csv"})


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Vault backend running at http://localhost:5000")
    print("📡 API endpoints:")
    print("   GET  /api/expenses          - List expenses")
    print("   POST /api/expenses          - Add expense")
    print("   GET  /api/budget            - Get budget limits & spending")
    print("   PUT  /api/budget            - Update budget limits")
    print("   GET  /api/rewards           - Get earned badges")
    print("   GET  /api/integrations      - List app integrations")
    print("   POST /api/integrations/:id/connect - Connect an app")
    print("   POST /api/integrations/:id/sync    - Sync transactions")
    print("   GET  /api/summary           - Full dashboard summary")
    print("   GET  /api/export/csv        - Download CSV")
    app.run(debug=True, port=5000)
