from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.billing import Bill, BillItem
from app.models.report import Expense
from app.models.inventory import Product
from sqlalchemy import func
from decimal import Decimal
from datetime import datetime, date, timedelta

reports_bp = Blueprint('reports', __name__)


def get_branch_id():
    return session.get('branch_id')


@reports_bp.route('/')
@login_required
def index():
    branch_id = get_branch_id()
    today = date.today()
    month_start = today.replace(day=1)

    date_from = request.args.get('date_from', month_start.strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', today.strftime('%Y-%m-%d'))

    try:
        d_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        d_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        d_from, d_to = month_start, today

    # Revenue from bills
    revenue = db.session.query(func.sum(Bill.total)).filter(
        Bill.branch_id == branch_id,
        func.date(Bill.bill_date) >= d_from,
        func.date(Bill.bill_date) <= d_to,
        Bill.status != 'cancelled'
    ).scalar() or Decimal('0')

    # COGS from bill items
    cogs_query = db.session.query(
        func.sum(BillItem.cost_price * BillItem.quantity)
    ).join(Bill).filter(
        Bill.branch_id == branch_id,
        func.date(Bill.bill_date) >= d_from,
        func.date(Bill.bill_date) <= d_to,
        Bill.status != 'cancelled'
    ).scalar() or Decimal('0')

    gross_profit = Decimal(str(revenue)) - Decimal(str(cogs_query))
    gross_margin = (gross_profit / Decimal(str(revenue)) * 100) if revenue > 0 else Decimal('0')

    # Expenses
    expenses = Expense.query.filter(
        Expense.branch_id == branch_id,
        Expense.expense_date >= d_from,
        Expense.expense_date <= d_to
    ).all()
    total_expenses = sum(e.amount for e in expenses)

    net_profit = gross_profit - Decimal(str(total_expenses))

    # Daily chart data
    daily_data = []
    current_day = d_from
    while current_day <= d_to and len(daily_data) < 60:
        day_revenue = db.session.query(func.sum(Bill.total)).filter(
            Bill.branch_id == branch_id,
            func.date(Bill.bill_date) == current_day,
            Bill.status != 'cancelled'
        ).scalar() or 0
        day_cogs = db.session.query(func.sum(BillItem.cost_price * BillItem.quantity)).join(Bill).filter(
            Bill.branch_id == branch_id,
            func.date(Bill.bill_date) == current_day,
            Bill.status != 'cancelled'
        ).scalar() or 0
        daily_data.append({
            'date': current_day.strftime('%d %b'),
            'revenue': float(day_revenue),
            'cogs': float(day_cogs),
            'profit': float(day_revenue) - float(day_cogs)
        })
        current_day += timedelta(days=1)

    # Top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(BillItem.quantity).label('total_qty'),
        func.sum(BillItem.total_price).label('total_revenue')
    ).join(BillItem, Product.id == BillItem.product_id).join(Bill).filter(
        Bill.branch_id == branch_id,
        func.date(Bill.bill_date) >= d_from,
        func.date(Bill.bill_date) <= d_to,
        Bill.status != 'cancelled'
    ).group_by(Product.id, Product.name).order_by(func.sum(BillItem.quantity).desc()).limit(10).all()

    # Category breakdown
    category_data = db.session.query(
        db.text('categories.name'),
        func.sum(BillItem.total_price).label('revenue')
    ).select_from(BillItem).join(Bill).join(Product, BillItem.product_id == Product.id).join(
        db.text('categories'), db.text('products.category_id = categories.id'), isouter=True
    ).filter(
        Bill.branch_id == branch_id,
        func.date(Bill.bill_date) >= d_from,
        func.date(Bill.bill_date) <= d_to,
        Bill.status != 'cancelled'
    ).group_by(db.text('categories.name')).all()

    return render_template('reports/index.html',
        revenue=float(revenue),
        cogs=float(cogs_query),
        gross_profit=float(gross_profit),
        gross_margin=float(gross_margin),
        total_expenses=float(total_expenses),
        net_profit=float(net_profit),
        expenses=expenses,
        daily_data=daily_data,
        top_products=top_products,
        category_data=category_data,
        date_from=date_from,
        date_to=date_to,
    )


@reports_bp.route('/expense/add', methods=['POST'])
@login_required
def add_expense():
    branch_id = get_branch_id()
    expense = Expense(
        branch_id=branch_id,
        category=request.form.get('category', 'misc'),
        amount=request.form.get('amount', 0),
        description=request.form.get('description', ''),
        expense_date=datetime.strptime(request.form.get('expense_date', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
        user_id=current_user.id
    )
    db.session.add(expense)
    db.session.commit()
    flash('Expense recorded!', 'success')
    return redirect(url_for('reports.index'))


@reports_bp.route('/expense/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'info')
    return redirect(url_for('reports.index'))
