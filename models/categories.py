from database import db

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(7))
    icon = db.Column(db.String(50), nullable=False)

    transactions = db.relationship(
        'Transaction',
        back_populates='category',
        lazy=True
    )

    def to_dict(self):
        return {    
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'color': self.color,
            'icon': self.icon
        }