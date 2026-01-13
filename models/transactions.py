from database import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_uid = db.Column(db.String(128), nullable=False)

    category_id = db.Column(
        db.Integer,
        db.ForeignKey('categories.id', ondelete='SET NULL'),
        nullable=True
    )

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    category = db.relationship(
        'Category',
        back_populates='transactions',
        lazy=True
    )

    budget_id = db.Column(
        db.Integer,
        db.ForeignKey('budgets.id', ondelete='SET NULL'),
        nullable=True
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_uid': self.user_uid,
            'category_id': self.category_id,
            'amount': float(self.amount),
            'date': self.date.isoformat()
        }
