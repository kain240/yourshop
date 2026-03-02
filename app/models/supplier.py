from app import db
from datetime import datetime


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    gst_no = db.Column(db.String(30))
    outstanding_amount = db.Column(db.Numeric(10, 2), default=0)  # amount we owe them
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('SupplierProduct', backref='supplier', lazy='dynamic')
    payments = db.relationship('SupplierPayment', backref='supplier', lazy='dynamic')
    batches = db.relationship('Batch', backref='supplier', lazy='dynamic',
                              foreign_keys='Batch.supplier_id')

    @property
    def last_payment(self):
        return self.payments.order_by(SupplierPayment.created_at.desc()).first()

    def __repr__(self):
        return f'<Supplier {self.name}>'


class SupplierProduct(db.Model):
    __tablename__ = 'supplier_products'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    supplier_sku = db.Column(db.String(50))  # supplier's own product code
    lead_time_days = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('supplier_id', 'product_id'),)


class SupplierPayment(db.Model):
    __tablename__ = 'supplier_payments'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(20), default='payment')  # payment, invoice (purchase adds to outstanding)
    method = db.Column(db.String(20))  # cash, bank, upi, cheque
    reference_no = db.Column(db.String(50))
    note = db.Column(db.Text)
    outstanding_before = db.Column(db.Numeric(10, 2), default=0)
    outstanding_after = db.Column(db.Numeric(10, 2), default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def __repr__(self):
        return f'<SupplierPayment {self.amount} to supplier {self.supplier_id}>'
