from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User, Branch
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        branch_id = request.form.get('branch_id', type=int)
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email, is_active=True).first()
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)

            # Set branch in session
            if branch_id:
                branch = Branch.query.get(branch_id)
                if branch:
                    session['branch_id'] = branch_id
                    session['branch_name'] = branch.name
            elif user.branch_id:
                session['branch_id'] = user.branch_id
                branch = Branch.query.get(user.branch_id)
                session['branch_name'] = branch.name if branch else ''

            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid email or password.', 'danger')

    branches = Branch.query.filter_by(is_active=True).all()
    return render_template('auth/login.html', branches=branches)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # If already registered users exist and someone accesses /register,
    # still allow it so new staff can be added via self-registration.
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        branch_name = request.form.get('branch_name', '').strip() or 'Main Branch'

        # Validation
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html', form_data=request.form)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', form_data=request.form)

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register.html', form_data=request.form)

        # Create default branch if none exists, or use the provided name
        branch = Branch.query.first()
        if not branch:
            branch = Branch(name=branch_name, address='', is_active=True)
            db.session.add(branch)
            db.session.flush()

        # First registered user is admin, subsequent ones are staff
        is_first_user = User.query.count() == 0
        role = 'admin' if is_first_user else 'staff'

        user = User(
            name=name,
            email=email,
            role=role,
            branch_id=branch.id,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f'Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form_data=None)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/switch-branch/<int:branch_id>')
@login_required
def switch_branch(branch_id):
    branch = Branch.query.get_or_404(branch_id)
    session['branch_id'] = branch.id
    session['branch_name'] = branch.name
    flash(f'Switched to branch: {branch.name}', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))
