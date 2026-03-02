from app import db
from datetime import datetime


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    barcode = db.Column(db.String(50), unique=True, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    unit = db.Column(db.String(20), default='pcs')  # pcs, kg, ltr, etc.
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_percent = db.Column(db.Numeric(5, 2), default=0)
    low_stock_threshold = db.Column(db.Integer, default=10)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batches = db.relationship('Batch', backref='product', lazy='dynamic', order_by='Batch.expiry_date')
    bill_items = db.relationship('BillItem', backref='product', lazy='dynamic')
    supplier_products = db.relationship('SupplierProduct', backref='product', lazy='dynamic')

    @property
    def total_quantity(self):
        return sum(b.quantity for b in self.batches.filter_by(is_active=True))

    @property
    def is_low_stock(self):
        return self.total_quantity <= self.low_stock_threshold

    @property
    def earliest_expiry(self):
        batch = self.batches.filter(
            Batch.is_active == True,
            Batch.expiry_date.isnot(None),
            Batch.quantity > 0
        ).order_by(Batch.expiry_date).first()
        return batch.expiry_date if batch else None

    def __repr__(self):
        return f'<Product {self.name}>'


class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_no = db.Column(db.String(50))
    expiry_date = db.Column(db.Date, nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    purchase_date = db.Column(db.Date, default=datetime.utcnow)
    purchase_price = db.Column(db.Numeric(10, 2), default=0)  # cost at time of purchase
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < datetime.utcnow().date()
        return False

    @property
    def days_to_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - datetime.utcnow().date()
            return delta.days
        return None

    def __repr__(self):
        return f'<Batch {self.batch_no} of Product {self.product_id}>'


class InventoryLog(db.Model):
    __tablename__ = 'inventory_logs'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    action = db.Column(db.String(20))  # add, deduct, adjust, return
    quantity_change = db.Column(db.Integer)
    reason = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')
    batch = db.relationship('Batch')
    user = db.relationship('User')
