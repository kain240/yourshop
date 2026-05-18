from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.billing import Bill, BillItem, Customer, Return
from app.models.inventory import Product, Batch, InventoryLog
from app.models.payment import Payment, CreditLedger
from app.services.pdf_service import generate_bill_pdf
from app.services.notification_service import send_bill_email, send_bill_whatsapp
from sqlalchemy import or_
from decimal import Decimal
from datetime import datetime, date
import json

billing_bp = Blueprint('billing', __name__)


def get_branch_id():
    return session.get('branch_id')


@billing_bp.route('/')
#@login_required
def index():
    branch_id = get_branch_id()
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Bill.query.filter_by(branch_id=branch_id)
    if q:
        query = query.join(Customer, isouter=True).filter(
            or_(Bill.bill_no.ilike(f'%{q}%'), Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%'))
        )
    if status:
        query = query.filter_by(status=status)
    if date_from:
        query = query.filter(Bill.bill_date >= date_from)
    if date_to:
        query = query.filter(Bill.bill_date <= date_to + ' 23:59:59')

    bills = query.order_by(Bill.bill_date.desc()).paginate(page=page, per_page=25)
    return render_template('billing/index.html', bills=bills, q=q, status=status,
                           date_from=date_from, date_to=date_to)


@billing_bp.route('/new', methods=['GET', 'POST'])
#@login_required
def new_bill():
    branch_id = get_branch_id()
    customers = Customer.query.filter_by(branch_id=branch_id, is_active=True).order_by(Customer.name).all()

    if request.method == 'POST':
        data = request.get_json()
        try:
            result = create_bill(data, branch_id, current_user.id)
            if result['success']:
                return jsonify({'success': True, 'bill_id': result['bill_id'], 'bill_no': result['bill_no']})
            else:
                return jsonify({'success': False, 'errors': result['errors']}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'errors': [str(e)]}), 500

    return render_template('billing/new_bill.html', customers=customers)


def create_bill(data, branch_id, user_id):
    errors = []
    items_data = data.get('items', [])

    if not items_data:
        return {'success': False, 'errors': ['No items in the bill.']}

    # Validate stock for all items first
    deductions = []
    for item in items_data:
        product = Product.query.get(item['product_id'])
        if not product or not product.is_active:
            errors.append(f'Product not found: {item.get("name", item["product_id"])}')
            continue
        total_qty = product.total_quantity
        req_qty = int(item['quantity'])
        if total_qty < req_qty:
            errors.append(f'Insufficient stock for "{product.name}": available {total_qty}, requested {req_qty}')
        else:
            deductions.append((product, req_qty))

    if errors:
        return {'success': False, 'errors': errors}

    # Create bill
    customer_id = data.get('customer_id') or None
    subtotal = Decimal('0')
    tax_total = Decimal('0')

    bill = Bill(
        customer_id=customer_id,
        branch_id=branch_id,
        user_id=user_id,
        bill_date=datetime.utcnow(),
        notes=data.get('notes', ''),
        delivery_method=data.get('delivery_method', 'none'),
        delivery_address=data.get('delivery_address', ''),
        status='paid'
    )
    db.session.add(bill)
    db.session.flush()

    # Create bill items and deduct inventory (FIFO by expiry)
    for item in items_data:
        product = Product.query.get(item['product_id'])
        req_qty = int(item['quantity'])
        unit_price = Decimal(str(item['unit_price']))
        tax_pct = Decimal(str(product.tax_percent))
        item_tax = (unit_price * req_qty * tax_pct / 100).quantize(Decimal('0.01'))
        item_total = (unit_price * req_qty + item_tax).quantize(Decimal('0.01'))

        # Deduct from batches FIFO
        remaining = req_qty
        batches_used = []
        available_batches = Batch.query.filter_by(
            product_id=product.id, is_active=True
        ).filter(Batch.quantity > 0).order_by(Batch.expiry_date.nullslast(), Batch.created_at).all()

        for batch in available_batches:
            if remaining <= 0:
                break
            deduct = min(batch.quantity, remaining)
            batch.quantity -= deduct
            remaining -= deduct
            batches_used.append((batch.id, deduct))
            log = InventoryLog(product_id=product.id, batch_id=batch.id, action='deduct',
                               quantity_change=-deduct, reason=f'Bill {bill.bill_no}', user_id=user_id)
            db.session.add(log)

        first_batch_id = batches_used[0][0] if batches_used else None
        bill_item = BillItem(
            bill_id=bill.id,
            product_id=product.id,
            batch_id=first_batch_id,
            product_name=product.name,
            quantity=req_qty,
            unit_price=unit_price,
            cost_price=product.cost_price,
            tax_percent=tax_pct,
            tax_amount=item_tax,
            total_price=item_total
        )
        db.session.add(bill_item)
        subtotal += unit_price * req_qty
        tax_total += item_tax

    discount_pct = Decimal(str(data.get('discount_percent', 0)))
    discount_amt = (subtotal * discount_pct / 100).quantize(Decimal('0.01'))
    total = subtotal - discount_amt + tax_total

    bill.subtotal = subtotal
    bill.discount_percent = discount_pct
    bill.discount_amount = discount_amt
    bill.tax_amount = tax_total
    bill.total = total

    # Payment
    payment_method = data.get('payment_method', 'cash')
    amount_paid = Decimal(str(data.get('amount_paid', total)))
    amount_due = total - amount_paid

    if amount_due > 0:
        if customer_id:
            bill.status = 'partial' if amount_paid > 0 else 'credit'
        else:
            bill.status = 'partial'
    else:
        bill.status = 'paid'

    bill.amount_paid = amount_paid
    bill.amount_due = amount_due

    if amount_paid > 0:
        payment = Payment(
            bill_id=bill.id,
            customer_id=customer_id,
            amount=amount_paid,
            method=payment_method,
            user_id=user_id
        )
        db.session.add(payment)

    if amount_due > 0 and customer_id:
        customer = Customer.query.get(customer_id)
        old_balance = customer.credit_balance
        customer.credit_balance += amount_due
        ledger = CreditLedger(
            customer_id=customer_id,
            amount=amount_due,
            entry_type='debit',
            description=f'Bill {bill.bill_no}',
            balance_after=customer.credit_balance,
            reference_id=bill.id,
            reference_type='bill'
        )
        db.session.add(ledger)

    db.session.commit()

    # Generate PDF
    try:
        pdf_path = generate_bill_pdf(bill.id)
        bill.pdf_path = pdf_path
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'PDF generation failed: {e}')

    # Send notification
    if bill.delivery_method == 'email' and bill.delivery_address:
        try:
            send_bill_email(bill.id, bill.delivery_address)
        except Exception as e:
            current_app.logger.error(f'Email send failed: {e}')
    elif bill.delivery_method == 'whatsapp' and bill.delivery_address:
        try:
            send_bill_whatsapp(bill.id, bill.delivery_address)
        except Exception as e:
            current_app.logger.error(f'WhatsApp send failed: {e}')

    return {'success': True, 'bill_id': bill.id, 'bill_no': bill.bill_no}


@billing_bp.route('/<int:bill_id>')
@login_required
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('billing/view_bill.html', bill=bill)


@billing_bp.route('/<int:bill_id>/pdf')
#@login_required
def download_pdf(bill_id):
    from flask import send_file
    bill = Bill.query.get_or_404(bill_id)
    if not bill.pdf_path or not __import__('os').path.exists(bill.pdf_path):
        pdf_path = generate_bill_pdf(bill_id)
        bill.pdf_path = pdf_path
        db.session.commit()
    return send_file(bill.pdf_path, mimetype='application/pdf',
                     download_name=f'{bill.bill_no}.pdf')


@billing_bp.route('/<int:bill_id>/send', methods=['POST'])
#@login_required
def send_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    method = request.form.get('method')
    address = request.form.get('address', '').strip()

    if not address:
        flash('Please provide an email or phone number.', 'danger')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))

    try:
        if method == 'email':
            send_bill_email(bill_id, address)
            flash(f'Bill sent to {address} via email!', 'success')
        elif method == 'whatsapp':
            send_bill_whatsapp(bill_id, address)
            flash(f'Bill sent to {address} via WhatsApp!', 'success')
        bill.delivery_method = method
        bill.delivery_address = address
        db.session.commit()
    except Exception as e:
        flash(f'Send failed: {str(e)}', 'danger')

    return redirect(url_for('billing.view_bill', bill_id=bill_id))


@billing_bp.route('/<int:bill_id>/return', methods=['GET', 'POST'])
#@login_required
def create_return(bill_id):
    bill = Bill.query.get_or_404(bill_id)

    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        qty = request.form.get('quantity', type=int)
        return_type = request.form.get('return_type', 'return')
        reason = request.form.get('reason', '')
        refund_method = request.form.get('refund_method', 'cash')

        bill_item = BillItem.query.filter_by(bill_id=bill_id, product_id=product_id).first()
        if not bill_item or qty > bill_item.quantity:
            flash('Invalid return quantity.', 'danger')
            return redirect(url_for('billing.create_return', bill_id=bill_id))

        refund_amount = (bill_item.unit_price * qty).quantize(Decimal('0.01'))

        ret = Return(
            return_no=f'RET-{bill.bill_no}-{product_id}',
            bill_id=bill_id,
            customer_id=bill.customer_id,
            product_id=product_id,
            batch_id=bill_item.batch_id,
            quantity=qty,
            return_type=return_type,
            reason=reason,
            refund_amount=refund_amount,
            refund_method=refund_method,
            user_id=current_user.id
        )
        db.session.add(ret)

        # Return stock to inventory
        if bill_item.batch_id:
            batch = Batch.query.get(bill_item.batch_id)
            if batch:
                batch.quantity += qty
        else:
            # Add to a new batch
            new_batch = Batch(product_id=product_id, quantity=qty, purchase_date=date.today())
            db.session.add(new_batch)

        log = InventoryLog(product_id=product_id, action='return',
                           quantity_change=qty, reason=f'Return from Bill {bill.bill_no}', user_id=current_user.id)
        db.session.add(log)

        # Handle credit refund
        if refund_method == 'credit' and bill.customer_id:
            customer = Customer.query.get(bill.customer_id)
            customer.credit_balance = max(0, customer.credit_balance - refund_amount)
            ledger = CreditLedger(customer_id=bill.customer_id, amount=refund_amount, entry_type='credit',
                                  description=f'Refund for return {ret.return_no}',
                                  balance_after=customer.credit_balance,
                                  reference_id=ret.id, reference_type='return')
            db.session.add(ledger)

        db.session.commit()
        flash('Return processed successfully!', 'success')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))

    return render_template('billing/return_form.html', bill=bill)
