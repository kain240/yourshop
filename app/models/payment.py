from app import db
from datetime import datetime


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(20))  # cash, razorpay, credit, upi, card
    razorpay_order_id = db.Column(db.String(100))
    razorpay_payment_id = db.Column(db.String(100))
    razorpay_signature = db.Column(db.String(255))
    status = db.Column(db.String(20), default='completed')  # pending, completed, failed, refunded
    note = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def __repr__(self):
        return f'<Payment {self.amount} for bill {self.bill_id}>'


class CreditLedger(db.Model):
    __tablename__ = 'credit_ledger'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    entry_type = db.Column(db.String(20))  # debit (customer owes more), credit (customer paid)
    description = db.Column(db.String(200))
    balance_after = db.Column(db.Numeric(10, 2), default=0)
    reference_id = db.Column(db.Integer)  # bill_id or payment_id
    reference_type = db.Column(db.String(20))  # bill, payment, return
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CreditLedger {self.entry_type} {self.amount} for customer {self.customer_id}>'
