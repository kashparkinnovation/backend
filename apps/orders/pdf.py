import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def generate_invoice_pdf(order) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    elements.append(Paragraph(f"<b>Invoice</b>", styles['Title']))
    elements.append(Paragraph(f"Order Number: {order.order_number}", styles['Normal']))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Vendor Details
    vendor = order.vendor
    if vendor:
        elements.append(Paragraph(f"<b>Vendor:</b> {vendor.business_name}", styles['Normal']))
        elements.append(Paragraph(f"GST: {vendor.gst_number}", styles['Normal']))
        elements.append(Paragraph(f"{vendor.address}, {vendor.city}, {vendor.state} - {vendor.pincode}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Customer Details
    elements.append(Paragraph(f"<b>Bill To:</b>", styles['Normal']))
    elements.append(Paragraph(f"{order.shipping_name}", styles['Normal']))
    elements.append(Paragraph(f"{order.shipping_address}", styles['Normal']))
    elements.append(Paragraph(f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}", styles['Normal']))
    elements.append(Paragraph(f"Phone: {order.shipping_phone}", styles['Normal']))
    if order.student_name:
        elements.append(Paragraph(f"Student: {order.student_name}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Items Table
    data = [["Product", "Size", "Color", "Qty", "Unit Price", "Total"]]
    for item in order.items.all():
        data.append([
            item.product_name,
            item.size,
            item.color,
            str(item.quantity),
            f"INR {item.unit_price}",
            f"INR {item.line_total}"
        ])

    table = Table(data, colWidths=[200, 60, 60, 50, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Totals
    elements.append(Paragraph(f"<b>Subtotal:</b> INR {order.subtotal}", styles['Normal']))
    elements.append(Paragraph(f"<b>Tax:</b> INR {order.tax_amount}", styles['Normal']))
    elements.append(Paragraph(f"<b>Shipping:</b> INR {order.shipping_amount}", styles['Normal']))
    elements.append(Paragraph(f"<b>Total Amount:</b> INR {order.total_amount}", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

def generate_delivery_slip_pdf(order) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    elements.append(Paragraph(f"<b>Delivery Slip</b>", styles['Title']))
    elements.append(Paragraph(f"Order Number: {order.order_number}", styles['Normal']))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # From (Vendor)
    vendor = order.vendor
    if vendor:
        elements.append(Paragraph(f"<b>From:</b> {vendor.business_name}", styles['Normal']))
        elements.append(Paragraph(f"{vendor.address}, {vendor.city}, {vendor.state} - {vendor.pincode}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # To (Customer)
    elements.append(Paragraph(f"<b>To:</b>", styles['Normal']))
    elements.append(Paragraph(f"{order.shipping_name}", styles['Normal']))
    elements.append(Paragraph(f"{order.shipping_address}", styles['Normal']))
    elements.append(Paragraph(f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}", styles['Normal']))
    elements.append(Paragraph(f"Phone: {order.shipping_phone}", styles['Normal']))
    if order.student_name:
        elements.append(Paragraph(f"Student: {order.student_name}", styles['Normal']))
    if order.school:
        elements.append(Paragraph(f"School: {order.school.name}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Items Table (No Prices)
    data = [["Product", "Size", "Color", "Qty"]]
    for item in order.items.all():
        data.append([
            item.product_name,
            item.size,
            item.color,
            str(item.quantity)
        ])

    table = Table(data, colWidths=[260, 80, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
