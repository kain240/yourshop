import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from flask import current_app


def generate_bill_pdf(bill_id):
    """Generate a professional PDF invoice for a bill and return its path"""
    from app.models.billing import Bill
    from app.models.user import Branch

    bill = Bill.query.get(bill_id)
    branch = Branch.query.get(bill.branch_id)

    upload_folder = current_app.config['UPLOAD_FOLDER']
    pdf_folder = os.path.join(upload_folder, 'bills')
    os.makedirs(pdf_folder, exist_ok=True)
    pdf_path = os.path.join(pdf_folder, f'{bill.bill_no}.pdf')

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor('#4F46E5')
    dark = colors.HexColor('#1e293b')
    muted = colors.HexColor('#64748b')

    title_style = ParagraphStyle('Title', fontSize=22, textColor=primary_color,
                                  fontName='Helvetica-Bold', alignment=TA_LEFT)
    heading_style = ParagraphStyle('Heading', fontSize=11, textColor=dark,
                                    fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('Normal', fontSize=9, textColor=dark, fontName='Helvetica')
    small_style = ParagraphStyle('Small', fontSize=8, textColor=muted, fontName='Helvetica')
    right_style = ParagraphStyle('Right', fontSize=9, textColor=dark, fontName='Helvetica', alignment=TA_RIGHT)

    elements = []

    # ---- Header ----
    header_data = [
        [Paragraph(branch.name if branch else 'YourShop', title_style),
         Paragraph(f'<b>INVOICE</b>', ParagraphStyle('inv', fontSize=18, textColor=muted,
                                                      fontName='Helvetica-Bold', alignment=TA_RIGHT))]
    ]
    header_table = Table(header_data, colWidths=[100*mm, 75*mm])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elements.append(header_table)
    elements.append(Spacer(1, 3*mm))

    # Branch info
    branch_info = f'{branch.address or ""}'
    if branch and branch.phone:
        branch_info += f' | Ph: {branch.phone}'
    if branch and branch.gst_no:
        branch_info += f' | GST: {branch.gst_no}'
    elements.append(Paragraph(branch_info, small_style))
    elements.append(HRFlowable(width='100%', thickness=1, color=primary_color, spaceAfter=4*mm))

    # Bill meta
    meta_data = [
        [Paragraph(f'<b>Bill No:</b> {bill.bill_no}', normal_style),
         Paragraph(f'<b>Date:</b> {bill.bill_date.strftime("%d %b %Y")}', right_style)],
        [Paragraph(f'<b>Customer:</b> {bill.customer_name}', normal_style),
         Paragraph(f'<b>Status:</b> {bill.status.upper()}', right_style)],
    ]
    if bill.customer and bill.customer.phone:
        meta_data.append([Paragraph(f'<b>Phone:</b> {bill.customer.phone}', normal_style), Paragraph('', right_style)])

    meta_table = Table(meta_data, colWidths=[100*mm, 75*mm])
    meta_table.setStyle(TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 2)]))
    elements.append(meta_table)
    elements.append(Spacer(1, 4*mm))

    # Items table
    items = bill.items.all()
    table_data = [['#', 'Product', 'Qty', 'Rate', 'Tax', 'Amount']]
    for i, item in enumerate(items, 1):
        table_data.append([
            str(i),
            item.product_name,
            f'{item.quantity} {item.product.unit if item.product else ""}',
            f'₹{item.unit_price:,.2f}',
            f'₹{item.tax_amount:,.2f}',
            f'₹{item.total_price:,.2f}'
        ])

    col_widths = [10*mm, 65*mm, 20*mm, 25*mm, 20*mm, 25*mm]
    items_table = Table(table_data, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 4*mm))

    # Totals
    totals_data = [
        ['', 'Subtotal', f'₹{bill.subtotal:,.2f}'],
        ['', f'Discount ({bill.discount_percent}%)', f'- ₹{bill.discount_amount:,.2f}'],
        ['', 'Tax', f'₹{bill.tax_amount:,.2f}'],
        ['', 'TOTAL', f'₹{bill.total:,.2f}'],
        ['', 'Amount Paid', f'₹{bill.amount_paid:,.2f}'],
        ['', 'Amount Due', f'₹{bill.amount_due:,.2f}'],
    ]
    totals_table = Table(totals_data, colWidths=[105*mm, 40*mm, 30*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (1, 3), (2, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 3), (2, 3), 11),
        ('TEXTCOLOR', (1, 3), (2, 3), primary_color),
        ('LINEABOVE', (1, 3), (2, 3), 1.5, primary_color),
        ('LINEBELOW', (1, 3), (2, 3), 1.5, primary_color),
        ('FONTNAME', (1, 5), (2, 5), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 5), (2, 5), colors.HexColor('#dc2626')),
    ]))
    elements.append(totals_table)

    # Footer
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=muted))
    elements.append(Spacer(1, 2*mm))
    if bill.notes:
        elements.append(Paragraph(f'<b>Notes:</b> {bill.notes}', small_style))
    elements.append(Paragraph('Thank you for your business!', ParagraphStyle('thanks', fontSize=9,
                               textColor=muted, fontName='Helvetica', alignment=TA_CENTER)))

    doc.build(elements)
    return pdf_path
