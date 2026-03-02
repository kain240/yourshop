from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app import db
from app.models.user import User, Branch

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
@login_required
def index():
    branches = Branch.query.filter_by(is_active=True).all()
    users = User.query.filter_by(is_active=True).all()
    return render_template('settings/index.html', branches=branches, users=users)


@settings_bp.route('/branch/add', methods=['POST'])
@login_required
def add_branch():
    if not current_user.is_admin():
        flash('Admin access required.', 'danger')
        return redirect(url_for('settings.index'))
    branch = Branch(
        name=request.form['name'],
        address=request.form.get('address', ''),
        phone=request.form.get('phone', ''),
        email=request.form.get('email', ''),
        gst_no=request.form.get('gst_no', '')
    )
    db.session.add(branch)
    db.session.commit()
    flash(f'Branch "{branch.name}" added!', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/user/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_manager():
        flash('Manager access required.', 'danger')
        return redirect(url_for('settings.index'))
    existing = User.query.filter_by(email=request.form['email']).first()
    if existing:
        flash('Email already in use.', 'danger')
        return redirect(url_for('settings.index'))
    user = User(
        name=request.form['name'],
        email=request.form['email'].strip().lower(),
        role=request.form.get('role', 'staff'),
        branch_id=request.form.get('branch_id', type=int)
    )
    user.set_password(request.form['password'])
    db.session.add(user)
    db.session.commit()
    flash(f'User "{user.name}" created!', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/user/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot deactivate yourself.', 'danger')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.name} {status}.', 'info')
    return redirect(url_for('settings.index'))
