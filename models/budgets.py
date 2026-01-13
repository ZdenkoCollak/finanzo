from database import db

class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    user_uid = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)
    transactions = db.relationship('Transaction', backref='budget', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_uid': self.user_uid,
            'balance': self.balance
        }