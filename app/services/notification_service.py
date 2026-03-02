import os
from flask import current_app


def send_bill_email(bill_id: int, email_address: str):
    """Send the bill PDF as an email attachment"""
    from app import mail
    from app.models.billing import Bill
    from app.models.user import Branch
    from app.services.pdf_service import generate_bill_pdf
    from flask_mail import Message

    bill = Bill.query.get(bill_id)
    branch = Branch.query.get(bill.branch_id)

    # Ensure PDF exists
    pdf_path = bill.pdf_path
    if not pdf_path or not os.path.exists(pdf_path):
        pdf_path = generate_bill_pdf(bill_id)

    subject = f'Invoice {bill.bill_no} from {branch.name if branch else "YourShop"}'
    body = f"""Dear {bill.customer_name},

Thank you for shopping with us!

Please find your invoice {bill.bill_no} for ₹{bill.total:,.2f} attached.

{f"Amount Due: ₹{bill.amount_due:,.2f}" if bill.amount_due > 0 else "Payment Status: Paid"}

Thank you,
{branch.name if branch else 'YourShop'} Team
"""

    msg = Message(subject=subject, recipients=[email_address], body=body)

    with open(pdf_path, 'rb') as f:
        msg.attach(f'{bill.bill_no}.pdf', 'application/pdf', f.read())

    mail.send(msg)


def send_bill_whatsapp(bill_id: int, phone_number: str):
    """Send a bill summary via WhatsApp using Twilio sandbox"""
    from twilio.rest import Client
    from flask import current_app
    from app.models.billing import Bill
    from app.models.user import Branch

    bill = Bill.query.get(bill_id)
    branch = Branch.query.get(bill.branch_id)

    # Normalize phone number
    phone = phone_number.strip().replace(' ', '').replace('-', '')
    if not phone.startswith('+'):
        phone = '+91' + phone  # Default to India

    items_text = '\n'.join([
        f'  • {item.product_name} x{item.quantity} = ₹{item.total_price:,.2f}'
        for item in bill.items.all()
    ])

    message = f"""🧾 *Invoice from {branch.name if branch else "YourShop"}*

Bill No: *{bill.bill_no}*
Date: {bill.bill_date.strftime('%d %b %Y')}

*Items:*
{items_text}

Subtotal: ₹{bill.subtotal:,.2f}
Discount: -₹{bill.discount_amount:,.2f}
Tax: ₹{bill.tax_amount:,.2f}
*Total: ₹{bill.total:,.2f}*

{f"⚠️ Amount Due: ₹{bill.amount_due:,.2f}" if bill.amount_due > 0 else "✅ Payment: Received"}

Thank you for shopping with us! 🛒
"""

    client = Client(
        current_app.config['TWILIO_ACCOUNT_SID'],
        current_app.config['TWILIO_AUTH_TOKEN']
    )

    client.messages.create(
        body=message,
        from_=current_app.config['TWILIO_WHATSAPP_FROM'],
        to=f'whatsapp:{phone}'
    )
