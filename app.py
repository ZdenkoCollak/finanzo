from flask import Flask, request, jsonify
from flask_cors import CORS
from database import db
from models.transactions import Transaction
from models.categories import Category
from models.budgets import Budget
from datetime import date, datetime, timedelta
from decimal import Decimal
import traceback
from sqlalchemy import func

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:FINANzo128@localhost/finanzo_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    print(db.engine.url)


def create_budget_for_user(user_uid: str):
    budget = Budget(user_uid=user_uid, balance=0.0)
    db.session.add(budget)
    db.session.commit()
    return budget


@app.route('/categories', methods=['GET'])
def get_categories():
    category_type = request.args.get('type')
    query = Category.query
    if category_type:
        query = query.filter(Category.type == category_type)
    categories = query.all()
    return jsonify([
        {
            'id': c.id,
            'name': c.name,
            'type': c.type,
            'color': c.color,
            'icon': c.icon
        }
        for c in categories
    ]), 200


@app.route('/transactions', methods=['POST'])
def add_transaction():
    data = request.get_json()
    user_uid = data['user_uid']

    budget = Budget.query.filter_by(user_uid=user_uid).first()
    if not budget:
        print(f"No budget found for {user_uid}, creating new one...")
        budget = create_budget_for_user(user_uid)

    try:
        amount = Decimal(str(data['amount']))

        transaction = Transaction(
            user_uid=user_uid,
            category_id=data['category_id'],
            amount=amount,
            date=datetime.fromisoformat(data['date']),
            budget_id=budget.id
        )
        db.session.add(transaction)

        budget.balance = Decimal(str(budget.balance))

        if data['category_type'] == 'income':
            budget.balance += amount
        else:
            budget.balance -= amount

        db.session.commit()
        return jsonify({'message': 'Transaction added', 'budget_balance': float(budget.balance)}), 201

    except Exception as e:
        db.session.rollback()
        print("Add transaction failed:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@app.route('/transactions/<string:user_uid>', methods=['GET'])
def get_transactions(user_uid):
    period = request.args.get('period', 'month')
    now = datetime.now()

    if period == 'day':
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
    elif period == 'week':
        start = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
        end = start + timedelta(days=7)
    elif period == 'month':
        start = datetime(now.year, now.month, 1)
        end = datetime(now.year + (now.month // 12), ((now.month % 12) + 1), 1)
    elif period == 'year':
        start = datetime(now.year, 1, 1)
        end = datetime(now.year + 1, 1, 1)
    elif period == 'all':
        start = datetime(1970, 1, 1)
        end = datetime(3000, 1, 1)
    else:
        start = datetime(now.year, now.month, 1)
        end = datetime(now.year + (now.month // 12), ((now.month % 12) + 1), 1)

    transactions = (
        db.session.query(Transaction, Category)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_uid == user_uid,
            Transaction.date >= start,
            Transaction.date < end
        )
        .order_by(Transaction.date.desc())
        .all()
    )

    return jsonify([
        {
            'id': t.id,
            'amount': float(t.amount),
            'date': t.date.isoformat(),
            'category': {
                'id': c.id,
                'name': c.name,
                'type': c.type,
                'color': c.color,
                'icon': c.icon
            }
        }
        for t, c in transactions
    ]), 200



@app.route('/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    budget = Budget.query.filter_by(user_uid=transaction.user_uid).first()
    if not budget:
        return jsonify({'error': 'Budget not found'}), 404
    
    budget.balance = Decimal(str(budget.balance))
    amount = Decimal(str(transaction.amount))

    
    if transaction.category.type == 'income':
        budget.balance -= amount
    else:
        budget.balance += amount
    db.session.delete(transaction)
    db.session.commit()
    return jsonify({'message': 'Transaction deleted'}), 200


@app.route('/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    try:
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        data = request.get_json()
        budget = Budget.query.get(transaction.budget_id)
        if not budget:
            return jsonify({'error': 'Budget not found'}), 404

        old_amount = Decimal(str(transaction.amount))
        old_category_type = transaction.category.type if transaction.category else None

        budget.balance = Decimal(str(budget.balance))
        if old_category_type == 'income':
            budget.balance -= old_amount
        elif old_category_type == 'expense':
            budget.balance += old_amount

        new_amount = Decimal(str(data['amount']))
        transaction.amount = new_amount
        transaction.category_id = data['category_id']

        try:
            transaction.date = datetime.fromisoformat(data['date'])
        except ValueError:
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d %H:%M:%S')

        new_category_type = data['category_type']
        if new_category_type == 'income':
            budget.balance += new_amount
        elif new_category_type == 'expense':
            budget.balance -= new_amount

        db.session.commit()
        return jsonify({'message': 'Transaction updated', 'budget_balance': float(budget.balance)}), 200

    except Exception as e:
        db.session.rollback()
        print("Update transaction failed:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@app.route('/statistics/by-category/<string:user_uid>/<string:type>', methods=['GET'])
def get_stats_by_category(user_uid, type):
    period = request.args.get('period', 'month')
    if type not in ['expense', 'income']:
        return jsonify({'error': 'Invalid category type'}), 400

    now = datetime.now()

    if period == 'day':
        start_datetime = datetime(now.year, now.month, now.day)
        end_datetime = start_datetime + timedelta(days=1)
    elif period == 'week':
        start_datetime = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
        end_datetime = start_datetime + timedelta(days=7)
    elif period == 'month':
        start_datetime = datetime(now.year, now.month, 1)
        if now.month == 12:
            end_datetime = datetime(now.year + 1, 1, 1)
        else:
            end_datetime = datetime(now.year, now.month + 1, 1)
    elif period == 'year':
        start_datetime = datetime(now.year, 1, 1)
        end_datetime = datetime(now.year + 1, 1, 1)
    elif period == 'all':
        start_datetime = datetime(1970, 1, 1)
        end_datetime = now + timedelta(2100, 1, 1)
    else:
        start_datetime = now - timedelta(days=30)  # default month
        end_datetime = now + timedelta(days=1)


    results = (
    db.session.query(
        Category.name,
        Category.color,
        func.coalesce(func.sum(Transaction.amount), 0).label('total')
    )
    .join(Transaction, Transaction.category_id == Category.id)
    .filter(
        Transaction.user_uid == user_uid,
        Category.type == type,
        Transaction.date >= start_datetime,
        Transaction.date < end_datetime
    )
    .group_by(Category.name, Category.color)
    .all()
    )

    return jsonify([
        {
            'category': name,
            'color': color,
            'total': float(total)
        }
        for name, color, total in results
    ]), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
