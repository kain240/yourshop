from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.billing import Bill, Customer
from app.models.payment import Payment
import razorpay
from decimal import Decimal
import hmac, hashlib

payments_bp = Blueprint('payments', __name__)


def get_razorpay_client():
    return razorpay.Client(auth=(
        current_app.config['RAZORPAY_KEY_ID'],
        current_app.config['RAZORPAY_KEY_SECRET']
    ))


@payments_bp.route('/create-order/<int:bill_id>', methods=['POST'])
@login_required
def create_order(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    amount_due = float(bill.amount_due)

    if amount_due <= 0:
        return jsonify({'error': 'No amount due'}), 400

    client = get_razorpay_client()
    order = client.order.create({
        'amount': int(amount_due * 100),  # in paise
        'currency': 'INR',
        'receipt': bill.bill_no,
        'notes': {'bill_id': bill.id, 'customer': bill.customer_name}
    })

    return jsonify({
        'order_id': order['id'],
        'amount': order['amount'],
        'currency': order['currency'],
        'key': current_app.config['RAZORPAY_KEY_ID'],
        'bill_no': bill.bill_no,
        'customer_name': bill.customer_name,
    })


@payments_bp.route('/verify', methods=['POST'])
@login_required
def verify_payment():
    data = request.get_json()
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    bill_id = data.get('bill_id')

    # Verify signature
    key_secret = current_app.config['RAZORPAY_KEY_SECRET'].encode()
    msg = f'{razorpay_order_id}|{razorpay_payment_id}'.encode()
    generated_signature = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

    if generated_signature != razorpay_signature:
        return jsonify({'success': False, 'error': 'Invalid signature'}), 400

    # Update bill and payment record
    bill = Bill.query.get_or_404(bill_id)
    payment = Payment(
        bill_id=bill_id,
        customer_id=bill.customer_id,
        amount=bill.amount_due,
        method='razorpay',
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        status='completed',
        user_id=current_user.id
    )
    db.session.add(payment)

    bill.amount_paid += bill.amount_due
    bill.amount_due = 0
    bill.status = 'paid'

    # Update customer credit balance
    if bill.customer_id:
        from app.models.payment import CreditLedger
        customer = Customer.query.get(bill.customer_id)
        customer.credit_balance = max(Decimal('0'), customer.credit_balance - payment.amount)
        ledger = CreditLedger(customer_id=bill.customer_id, amount=payment.amount,
                              entry_type='credit', description=f'Razorpay payment {razorpay_payment_id}',
                              balance_after=customer.credit_balance, reference_type='payment')
        db.session.add(ledger)

    db.session.commit()
    return jsonify({'success': True, 'bill_no': bill.bill_no})


@payments_bp.route('/payment-link/<int:bill_id>', methods=['POST'])
@login_required
def create_payment_link(bill_id):
    """Generate a Razorpay payment link to share with customer"""
    bill = Bill.query.get_or_404(bill_id)
    if float(bill.amount_due) <= 0:
        flash('No outstanding amount for this bill.', 'warning')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))

    client = get_razorpay_client()
    link_data = {
        'amount': int(float(bill.amount_due) * 100),
        'currency': 'INR',
        'accept_partial': False,
        'description': f'Payment for Bill {bill.bill_no}',
        'customer': {},
        'notify': {'sms': False, 'email': False},
        'reminder_enable': False,
    }
    if bill.customer:
        link_data['customer'] = {
            'name': bill.customer.name,
            'contact': bill.customer.phone or '',
            'email': bill.customer.email or '',
        }

    try:
        plink = client.payment_link.create(link_data)
        flash(f'Payment link created: {plink["short_url"]}', 'success')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))
    except Exception as e:
        flash(f'Failed to create payment link: {e}', 'danger')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))
