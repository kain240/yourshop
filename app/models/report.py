from app import db
from datetime import datetime


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    category = db.Column(db.String(80))  # rent, electricity, salary, misc
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    expense_date = db.Column(db.Date, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch')
    user = db.relationship('User')

    def __repr__(self):
        return f'<Expense {self.category} {self.amount}>'
