from flask import Blueprint, render_template, session
from flask_login import login_required, current_user
from app import db
from app.models.billing import Bill, Customer
from app.models.inventory import Product, Batch
from app.models.supplier import Supplier
from app.models.payment import Payment
from app.models.report import Expense
from sqlalchemy import func
from datetime import datetime, date, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


def get_branch_id():
    return session.get('branch_id')


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    branch_id = get_branch_id()
    today = date.today()
    month_start = today.replace(day=1)

    # Today's sales
    today_bills = Bill.query.filter(
        Bill.branch_id == branch_id,
        func.date(Bill.bill_date) == today,
        Bill.status != 'cancelled'
    ).all()
    today_revenue = sum(float(b.total) for b in today_bills)
    today_bills_count = len(today_bills)

    # Monthly revenue
    monthly_bills = Bill.query.filter(
        Bill.branch_id == branch_id,
        Bill.bill_date >= month_start,
        Bill.status != 'cancelled'
    ).all()
    monthly_revenue = sum(float(b.total) for b in monthly_bills)

    # Low stock items
    products = Product.query.filter_by(branch_id=branch_id, is_active=True).all()
    low_stock = [p for p in products if p.is_low_stock]

    # Expiring in 30 days
    expiry_threshold = today + timedelta(days=30)
    expiring_batches = Batch.query.join(Product).filter(
        Product.branch_id == branch_id,
        Product.is_active == True,
        Batch.is_active == True,
        Batch.expiry_date.isnot(None),
        Batch.expiry_date <= expiry_threshold,
        Batch.expiry_date >= today,
        Batch.quantity > 0
    ).order_by(Batch.expiry_date).limit(10).all()

    # Pending dues from customers
    pending_dues = db.session.query(func.sum(Customer.credit_balance)).filter(
        Customer.branch_id == branch_id
    ).scalar() or 0

    # Supplier outstanding
    supplier_outstanding = db.session.query(func.sum(Supplier.outstanding_amount)).filter(
        Supplier.branch_id == branch_id
    ).scalar() or 0

    # Last 7 days sales for chart
    sales_chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_total = db.session.query(func.sum(Bill.total)).filter(
            Bill.branch_id == branch_id,
            func.date(Bill.bill_date) == day,
            Bill.status != 'cancelled'
        ).scalar() or 0
        sales_chart.append({'date': day.strftime('%d %b'), 'amount': float(day_total)})

    # Monthly P&L quick
    monthly_cogs = db.session.query(
        func.sum(db.cast(Bill.query.with_entities(func.sum(
            db.cast(db.text('bill_items.cost_price * bill_items.quantity'), db.Numeric)
        )).filter(
            Bill.branch_id == branch_id,
            Bill.bill_date >= month_start
        ).scalar() or 0, db.Numeric))
    ).scalar() or 0

    monthly_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.branch_id == branch_id,
        Expense.expense_date >= month_start
    ).scalar() or 0

    return render_template('dashboard/index.html',
        today_revenue=today_revenue,
        today_bills_count=today_bills_count,
        monthly_revenue=monthly_revenue,
        low_stock=low_stock,
        expiring_batches=expiring_batches,
        pending_dues=float(pending_dues),
        supplier_outstanding=float(supplier_outstanding),
        sales_chart=sales_chart,
        monthly_expenses=float(monthly_expenses),
    )
