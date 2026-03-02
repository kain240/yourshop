from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models.inventory import Product, Batch, Category, InventoryLog
from app.models.user import Branch
from app.services.barcode_service import generate_barcode
from sqlalchemy import or_
from datetime import datetime, date, timedelta
import os

inventory_bp = Blueprint('inventory', __name__)


def get_branch_id():
    return session.get('branch_id')


@inventory_bp.route('/')
@login_required
def index():
    branch_id = get_branch_id()
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    stock_filter = request.args.get('stock', '')
    expiry_filter = request.args.get('expiry', '')

    query = Product.query.filter_by(branch_id=branch_id, is_active=True)
    if q:
        query = query.filter(or_(
            Product.name.ilike(f'%{q}%'),
            Product.barcode.ilike(f'%{q}%')
        ))
    if category_id:
        query = query.filter_by(category_id=category_id)

    products = query.order_by(Product.name).all()

    today = date.today()
    expiry_threshold = today + timedelta(days=30)

    if stock_filter == 'low':
        products = [p for p in products if p.is_low_stock]
    elif stock_filter == 'out':
        products = [p for p in products if p.total_quantity == 0]

    if expiry_filter == 'expiring':
        products = [p for p in products if p.earliest_expiry and p.earliest_expiry <= expiry_threshold]
    elif expiry_filter == 'expired':
        products = [p for p in products if p.earliest_expiry and p.earliest_expiry < today]

    categories = Category.query.all()
    return render_template('inventory/index.html',
        products=products, categories=categories, q=q,
        category_id=category_id, stock_filter=stock_filter, expiry_filter=expiry_filter
    )


@inventory_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    branch_id = get_branch_id()
    categories = Category.query.all()

    if request.method == 'POST':
        barcode = request.form.get('barcode', '').strip() or None
        if barcode:
            existing = Product.query.filter_by(barcode=barcode).first()
            if existing:
                flash('A product with this barcode already exists.', 'danger')
                return render_template('inventory/product_form.html', categories=categories)

        product = Product(
            name=request.form['name'],
            barcode=barcode,
            category_id=request.form.get('category_id', type=int),
            unit=request.form.get('unit', 'pcs'),
            cost_price=request.form.get('cost_price', 0),
            selling_price=request.form.get('selling_price', 0),
            tax_percent=request.form.get('tax_percent', 0),
            low_stock_threshold=request.form.get('low_stock_threshold', 10),
            branch_id=branch_id
        )
        db.session.add(product)
        db.session.flush()

        # Add initial batch if quantity provided
        qty = request.form.get('initial_qty', 0, type=int)
        if qty > 0:
            batch = Batch(
                product_id=product.id,
                batch_no=request.form.get('batch_no', '').strip() or None,
                expiry_date=parse_date(request.form.get('expiry_date')),
                quantity=qty,
                purchase_price=request.form.get('cost_price', 0),
                purchase_date=date.today()
            )
            db.session.add(batch)
            log = InventoryLog(product_id=product.id, action='add',
                               quantity_change=qty, reason='Initial stock', user_id=current_user.id)
            db.session.add(log)

        db.session.commit()
        flash(f'Product "{product.name}" added successfully!', 'success')
        return redirect(url_for('inventory.index'))

    return render_template('inventory/product_form.html', categories=categories, product=None)


@inventory_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()

    if request.method == 'POST':
        barcode = request.form.get('barcode', '').strip() or None
        if barcode and barcode != product.barcode:
            existing = Product.query.filter(Product.barcode == barcode, Product.id != product_id).first()
            if existing:
                flash('A product with this barcode already exists.', 'danger')
                return render_template('inventory/product_form.html', product=product, categories=categories)

        product.name = request.form['name']
        product.barcode = barcode
        product.category_id = request.form.get('category_id', type=int)
        product.unit = request.form.get('unit', 'pcs')
        product.cost_price = request.form.get('cost_price', 0)
        product.selling_price = request.form.get('selling_price', 0)
        product.tax_percent = request.form.get('tax_percent', 0)
        product.low_stock_threshold = request.form.get('low_stock_threshold', 10)
        product.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Product "{product.name}" updated!', 'success')
        return redirect(url_for('inventory.index'))

    return render_template('inventory/product_form.html', product=product, categories=categories)


@inventory_bp.route('/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False  # Soft delete
    db.session.commit()
    flash(f'Product "{product.name}" deactivated.', 'info')
    return redirect(url_for('inventory.index'))


@inventory_bp.route('/<int:product_id>/batches')
@login_required
def batches(product_id):
    product = Product.query.get_or_404(product_id)
    batches = Batch.query.filter_by(product_id=product_id, is_active=True).order_by(Batch.expiry_date).all()
    return render_template('inventory/batches.html', product=product, batches=batches)


@inventory_bp.route('/<int:product_id>/add-batch', methods=['POST'])
@login_required
def add_batch(product_id):
    product = Product.query.get_or_404(product_id)
    qty = request.form.get('quantity', 0, type=int)
    batch = Batch(
        product_id=product_id,
        batch_no=request.form.get('batch_no', '').strip() or None,
        expiry_date=parse_date(request.form.get('expiry_date')),
        quantity=qty,
        purchase_price=request.form.get('purchase_price', product.cost_price),
        supplier_id=request.form.get('supplier_id', type=int),
        purchase_date=date.today()
    )
    db.session.add(batch)
    log = InventoryLog(product_id=product_id, batch_id=batch.id, action='add',
                       quantity_change=qty, reason='Batch added', user_id=current_user.id)
    db.session.add(log)
    db.session.commit()
    flash('Batch added successfully!', 'success')
    return redirect(url_for('inventory.batches', product_id=product_id))


@inventory_bp.route('/search-api')
@login_required
def search_api():
    """JSON endpoint for POS barcode/name search"""
    branch_id = get_branch_id()
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    products = Product.query.filter(
        Product.branch_id == branch_id,
        Product.is_active == True,
        or_(Product.name.ilike(f'%{q}%'), Product.barcode == q)
    ).limit(10).all()
    result = []
    for p in products:
        result.append({
            'id': p.id,
            'name': p.name,
            'barcode': p.barcode,
            'selling_price': float(p.selling_price),
            'cost_price': float(p.cost_price),
            'tax_percent': float(p.tax_percent),
            'unit': p.unit,
            'quantity': p.total_quantity,
        })
    return jsonify(result)


@inventory_bp.route('/<int:product_id>/barcode')
@login_required
def barcode_view(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.barcode:
        flash('This product has no barcode assigned.', 'warning')
        return redirect(url_for('inventory.index'))
    path = generate_barcode(product.barcode, product.name)
    return send_file(path, mimetype='image/png', as_attachment=True,
                     download_name=f'barcode_{product.barcode}.png')


@inventory_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            cat = Category(name=name, description=request.form.get('description', ''))
            db.session.add(cat)
            db.session.commit()
            flash(f'Category "{name}" added.', 'success')
    all_cats = Category.query.order_by(Category.name).all()
    return render_template('inventory/categories.html', categories=all_cats)


def parse_date(date_str):
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return None
