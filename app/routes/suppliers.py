from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.supplier import Supplier, SupplierProduct, SupplierPayment
from app.models.inventory import Product, Batch
from sqlalchemy import or_
from decimal import Decimal
from datetime import datetime, date

suppliers_bp = Blueprint('suppliers', __name__)


def get_branch_id():
    return session.get('branch_id')


@suppliers_bp.route('/')
@login_required
def index():
    branch_id = get_branch_id()
    q = request.args.get('q', '')
    query = Supplier.query.filter_by(branch_id=branch_id, is_active=True)
    if q:
        query = query.filter(or_(Supplier.name.ilike(f'%{q}%'), Supplier.phone.ilike(f'%{q}%')))
    suppliers = query.order_by(Supplier.name).all()
    return render_template('suppliers/index.html', suppliers=suppliers, q=q)


@suppliers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    branch_id = get_branch_id()
    if request.method == 'POST':
        supplier = Supplier(
            name=request.form['name'],
            contact_person=request.form.get('contact_person', ''),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
            address=request.form.get('address', ''),
            gst_no=request.form.get('gst_no', ''),
            branch_id=branch_id
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f'Supplier "{supplier.name}" added!', 'success')
        return redirect(url_for('suppliers.index'))
    return render_template('suppliers/supplier_form.html', supplier=None)


@suppliers_bp.route('/<int:supplier_id>')
@login_required
def view_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    payments = supplier.payments.order_by(SupplierPayment.created_at.desc()).limit(30).all()
    linked_products = db.session.query(Product).join(SupplierProduct).filter(
        SupplierProduct.supplier_id == supplier_id).all()
    return render_template('suppliers/view_supplier.html', supplier=supplier,
                           payments=payments, linked_products=linked_products)


@suppliers_bp.route('/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.contact_person = request.form.get('contact_person', '')
        supplier.phone = request.form.get('phone', '')
        supplier.email = request.form.get('email', '')
        supplier.address = request.form.get('address', '')
        supplier.gst_no = request.form.get('gst_no', '')
        db.session.commit()
        flash('Supplier updated!', 'success')
        return redirect(url_for('suppliers.view_supplier', supplier_id=supplier_id))
    return render_template('suppliers/supplier_form.html', supplier=supplier)


@suppliers_bp.route('/<int:supplier_id>/pay', methods=['POST'])
@login_required
def record_payment(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    amount = Decimal(str(request.form.get('amount', 0)))
    method = request.form.get('method', 'cash')
    ref_no = request.form.get('reference_no', '')
    note = request.form.get('note', '')

    if amount <= 0:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('suppliers.view_supplier', supplier_id=supplier_id))

    outstanding_before = supplier.outstanding_amount
    supplier.outstanding_amount = max(Decimal('0'), supplier.outstanding_amount - amount)

    payment = SupplierPayment(
        supplier_id=supplier_id, amount=amount, payment_type='payment',
        method=method, reference_no=ref_no, note=note,
        outstanding_before=outstanding_before,
        outstanding_after=supplier.outstanding_amount,
        user_id=current_user.id
    )
    db.session.add(payment)
    db.session.commit()
    flash(f'Payment of ₹{amount} to {supplier.name} recorded. Outstanding: ₹{supplier.outstanding_amount}', 'success')
    return redirect(url_for('suppliers.view_supplier', supplier_id=supplier_id))


@suppliers_bp.route('/<int:supplier_id>/purchase', methods=['POST'])
@login_required
def record_purchase(supplier_id):
    """Record a purchase from supplier (adds stock + increases outstanding)"""
    supplier = Supplier.query.get_or_404(supplier_id)
    product_id = request.form.get('product_id', type=int)
    qty = request.form.get('quantity', 0, type=int)
    purchase_price = Decimal(str(request.form.get('purchase_price', 0)))
    total_invoice = purchase_price * qty
    batch_no = request.form.get('batch_no', '')
    expiry_date_str = request.form.get('expiry_date', '')

    expiry_date = None
    if expiry_date_str:
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    batch = Batch(
        product_id=product_id,
        batch_no=batch_no or None,
        expiry_date=expiry_date,
        quantity=qty,
        purchase_price=purchase_price,
        supplier_id=supplier_id,
        purchase_date=date.today()
    )
    db.session.add(batch)

    # Update supplier outstanding
    outstanding_before = supplier.outstanding_amount
    supplier.outstanding_amount += total_invoice
    inv_payment = SupplierPayment(
        supplier_id=supplier_id, amount=total_invoice, payment_type='invoice',
        note=f'Purchase: {qty} units of product #{product_id}',
        outstanding_before=outstanding_before,
        outstanding_after=supplier.outstanding_amount,
        user_id=current_user.id
    )
    db.session.add(inv_payment)
    db.session.commit()
    flash(f'Purchase recorded. ₹{total_invoice} added to {supplier.name} outstanding.', 'success')
    return redirect(url_for('suppliers.view_supplier', supplier_id=supplier_id))


@suppliers_bp.route('/<int:supplier_id>/link-product', methods=['POST'])
@login_required
def link_product(supplier_id):
    product_id = request.form.get('product_id', type=int)
    if product_id:
        existing = SupplierProduct.query.filter_by(supplier_id=supplier_id, product_id=product_id).first()
        if not existing:
            sp = SupplierProduct(supplier_id=supplier_id, product_id=product_id)
            db.session.add(sp)
            db.session.commit()
            flash('Product linked to supplier!', 'success')
    return redirect(url_for('suppliers.view_supplier', supplier_id=supplier_id))
