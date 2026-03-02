from app import db
from datetime import datetime
import random
import string


def generate_bill_no():
    prefix = 'INV'
    timestamp = datetime.utcnow().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.digits, k=4))
    return f'{prefix}-{timestamp}-{random_part}'


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    credit_limit = db.Column(db.Numeric(10, 2), default=0)
    credit_balance = db.Column(db.Numeric(10, 2), default=0)  # outstanding to pay
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bills = db.relationship('Bill', backref='customer', lazy='dynamic')
    payments = db.relationship('Payment', backref='customer', lazy='dynamic')
    returns = db.relationship('Return', backref='customer', lazy='dynamic')
    ledger_entries = db.relationship('CreditLedger', backref='customer', lazy='dynamic')

    def __repr__(self):
        return f'<Customer {self.name}>'


class Bill(db.Model):
    __tablename__ = 'bills'
    id = db.Column(db.Integer, primary_key=True)
    bill_no = db.Column(db.String(30), unique=True, nullable=False, default=generate_bill_no)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bill_date = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    discount_percent = db.Column(db.Numeric(5, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    amount_paid = db.Column(db.Numeric(10, 2), default=0)
    amount_due = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(20), default='paid')  # paid, partial, credit, cancelled
    notes = db.Column(db.Text)
    delivery_method = db.Column(db.String(20))  # email, whatsapp, none
    delivery_address = db.Column(db.String(200))  # email or phone for delivery
    pdf_path = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('BillItem', backref='bill', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='bill', lazy='dynamic')
    returns = db.relationship('Return', backref='bill', lazy='dynamic')
    user = db.relationship('User')

    @property
    def customer_name(self):
        return self.customer.name if self.customer else 'Walk-in Customer'

    def __repr__(self):
        return f'<Bill {self.bill_no}>'


class BillItem(db.Model):
    __tablename__ = 'bill_items'
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    product_name = db.Column(db.String(200))   # snapshot at time of billing
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_percent = db.Column(db.Numeric(5, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    batch = db.relationship('Batch')

    def __repr__(self):
        return f'<BillItem {self.product_name} x{self.quantity}>'


class Return(db.Model):
    __tablename__ = 'returns'
    id = db.Column(db.Integer, primary_key=True)
    return_no = db.Column(db.String(30), unique=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    return_type = db.Column(db.String(20), default='return')  # return, exchange
    reason = db.Column(db.Text)
    refund_amount = db.Column(db.Numeric(10, 2), default=0)
    refund_method = db.Column(db.String(20))  # cash, credit, razorpay
    exchange_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', foreign_keys=[product_id])
    exchange_product = db.relationship('Product', foreign_keys=[exchange_product_id])
    user = db.relationship('User')
    batch = db.relationship('Batch')

    def __repr__(self):
        return f'<Return {self.return_no}>'
