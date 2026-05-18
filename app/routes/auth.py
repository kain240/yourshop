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
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('auth.register'))

        # Create a default branch if none exists
        branch = Branch.query.first()
        if not branch:
            branch = Branch(name='Main Branch', is_active=True)
            db.session.add(branch)
            db.session.commit()

        user = User(name=name, email=email, role='admin', branch_id=branch.id, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return '''
        <form method="POST">
            <input name="name" placeholder="Name" required><br>
            <input name="email" placeholder="Email" required><br>
            <input name="password" type="password" placeholder="Password" required><br>
            <button type="submit">Register</button>
        </form>
    '''


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
