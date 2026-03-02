from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.billing import Customer, Bill
from app.models.payment import Payment, CreditLedger
from sqlalchemy import or_
from decimal import Decimal
from datetime import datetime

customers_bp = Blueprint('customers', __name__)


def get_branch_id():
    return session.get('branch_id')


@customers_bp.route('/')
@login_required
def index():
    branch_id = get_branch_id()
    q = request.args.get('q', '')
    query = Customer.query.filter_by(branch_id=branch_id, is_active=True)
    if q:
        query = query.filter(or_(Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%'), Customer.email.ilike(f'%{q}%')))
    customers = query.order_by(Customer.name).all()
    return render_template('customers/index.html', customers=customers, q=q)


@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    branch_id = get_branch_id()
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
            address=request.form.get('address', ''),
            credit_limit=request.form.get('credit_limit', 0),
            branch_id=branch_id
        )
        db.session.add(customer)
        db.session.commit()
        flash(f'Customer "{customer.name}" added!', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/customer_form.html', customer=None)


@customers_bp.route('/<int:customer_id>')
@login_required
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    bills = customer.bills.order_by(Bill.bill_date.desc()).limit(20).all()
    ledger = customer.ledger_entries.order_by(CreditLedger.created_at.desc()).limit(30).all()
    return render_template('customers/view_customer.html', customer=customer, bills=bills, ledger=ledger)


@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.phone = request.form.get('phone', '')
        customer.email = request.form.get('email', '')
        customer.address = request.form.get('address', '')
        customer.credit_limit = request.form.get('credit_limit', 0)
        db.session.commit()
        flash('Customer updated!', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))
    return render_template('customers/customer_form.html', customer=customer)


@customers_bp.route('/<int:customer_id>/pay', methods=['POST'])
@login_required
def record_payment(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    amount = Decimal(str(request.form.get('amount', 0)))
    method = request.form.get('method', 'cash')
    note = request.form.get('note', '')

    if amount <= 0:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

    payment = Payment(customer_id=customer_id, amount=amount, method=method,
                      note=note, status='completed', user_id=current_user.id)
    db.session.add(payment)

    old_balance = customer.credit_balance
    customer.credit_balance = max(Decimal('0'), customer.credit_balance - amount)
    ledger = CreditLedger(customer_id=customer_id, amount=amount, entry_type='credit',
                          description=f'Payment received - {method}',
                          balance_after=customer.credit_balance, reference_type='payment')
    db.session.add(ledger)
    db.session.commit()
    flash(f'Payment of ₹{amount} recorded. Outstanding: ₹{customer.credit_balance}', 'success')
    return redirect(url_for('customers.view_customer', customer_id=customer_id))


@customers_bp.route('/search')
@login_required
def search_api():
    branch_id = get_branch_id()
    q = request.args.get('q', '')
    customers = Customer.query.filter(
        Customer.branch_id == branch_id,
        Customer.is_active == True,
        or_(Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%'))
    ).limit(10).all()
    return jsonify([{'id': c.id, 'name': c.name, 'phone': c.phone,
                     'credit_balance': float(c.credit_balance)} for c in customers])
