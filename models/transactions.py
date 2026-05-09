from db import db
from datetime import datetime


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cashier_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(
        db.Integer, db.ForeignKey('customer.id'), nullable=True)
    total_amount = db.Column(db.Integer, nullable=False)
    items_count = db.Column(db.Integer, default=0)
    items = db.Column(db.JSON, nullable=False)  # Store items as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'cashier_id': self.cashier_id,
            'customer_id': self.customer_id,
            'total_amount': self.total_amount,
            'items_count': self.items_count,
            'items': self.items,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
