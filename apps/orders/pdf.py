"""
Professional Tax Invoice & Delivery Slip PDF generation.
Styled similar to Amazon invoices — eSchoolKart branded,
with parent, student, and school details.
"""
import io
import os
from decimal import Decimal

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

# ─── Colour palette ──────────────────────────────────────────────────────────
BRAND_BLUE   = colors.HexColor('#1a3a5c')
BRAND_ORANGE = colors.HexColor('#f57c20')
HEADER_BG    = colors.HexColor('#1a3a5c')
HEADER_TEXT  = colors.white
ROW_ALT      = colors.HexColor('#f8fafc')
BORDER_GREY  = colors.HexColor('#cbd5e1')
TEXT_DARK     = colors.HexColor('#0f172a')
TEXT_MUTED    = colors.HexColor('#64748b')

PAGE_W, PAGE_H = A4  # 595.27, 841.89 pts


def _logo_path():
    """Resolve the eSchoolKart logo stored in MEDIA_ROOT."""
    candidates = [
        os.path.join(settings.MEDIA_ROOT, 'eschoolkart-logo.jpeg'),
        os.path.join(settings.MEDIA_ROOT, 'eschoolkart-logo.png'),
        os.path.join(settings.MEDIA_ROOT, 'logo.png'),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _amount_in_words(amount):
    """Convert a Decimal/float amount to Indian English words."""
    try:
        from num2words import num2words
        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))
        words = num2words(rupees, lang='en_IN').title()
        if paise:
            paise_words = num2words(paise, lang='en_IN').title()
            return f'INR {words} Rupees And {paise_words} Paise Only.'
        return f'INR {words} Rupees Only.'
    except Exception:
        return f'INR {amount}'


def _styles():
    """Create a custom style-sheet."""
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle('InvTitle', fontSize=14, fontName='Helvetica-Bold',
                          textColor=BRAND_BLUE, spaceAfter=2))
    ss.add(ParagraphStyle('InvSubtitle', fontSize=8, fontName='Helvetica',
                          textColor=TEXT_MUTED, spaceAfter=1))
    ss.add(ParagraphStyle('SectionHead', fontSize=9, fontName='Helvetica-Bold',
                          textColor=BRAND_BLUE, spaceBefore=6, spaceAfter=3,
                          borderWidth=0, borderPadding=0))
    ss.add(ParagraphStyle('LabelStyle', fontSize=7.5, fontName='Helvetica-Bold',
                          textColor=TEXT_MUTED))
    ss.add(ParagraphStyle('ValueStyle', fontSize=8, fontName='Helvetica',
                          textColor=TEXT_DARK, leading=11))
    ss.add(ParagraphStyle('ValueBold', fontSize=8.5, fontName='Helvetica-Bold',
                          textColor=TEXT_DARK, leading=11))
    ss.add(ParagraphStyle('SmallMuted', fontSize=7, fontName='Helvetica',
                          textColor=TEXT_MUTED, leading=9))
    ss.add(ParagraphStyle('RightAligned', fontSize=8, fontName='Helvetica',
                          textColor=TEXT_DARK, alignment=TA_RIGHT))
    ss.add(ParagraphStyle('RightBold', fontSize=9, fontName='Helvetica-Bold',
                          textColor=TEXT_DARK, alignment=TA_RIGHT))
    ss.add(ParagraphStyle('CenterBold', fontSize=8, fontName='Helvetica-Bold',
                          textColor=TEXT_DARK, alignment=TA_CENTER))
    ss.add(ParagraphStyle('Footer', fontSize=7, fontName='Helvetica',
                          textColor=TEXT_MUTED, leading=9))
    ss.add(ParagraphStyle('TotalLabel', fontSize=10, fontName='Helvetica-Bold',
                          textColor=BRAND_BLUE, alignment=TA_RIGHT))
    ss.add(ParagraphStyle('TotalValue', fontSize=12, fontName='Helvetica-Bold',
                          textColor=BRAND_BLUE, alignment=TA_RIGHT))
    return ss


# ─── Invoice PDF ──────────────────────────────────────────────────────────────

def generate_invoice_pdf(order) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=25*mm, leftMargin=25*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    ss = _styles()
    elements = []
    usable_width = PAGE_W - 50*mm  # left+right margins

    # ── HEADER: "TAX INVOICE" + Logo ─────────────────────────────────────
    logo_file = _logo_path()
    header_left = []
    header_left.append(Paragraph('<b>TAX INVOICE</b>', ss['InvTitle']))
    header_left.append(Paragraph('ORIGINAL FOR RECIPIENT', ss['SmallMuted']))

    if logo_file:
        try:
            logo_img = Image(logo_file, width=45*mm, height=18*mm)
            logo_img.hAlign = 'RIGHT'
        except Exception:
            logo_img = Paragraph('', ss['InvSubtitle'])
    else:
        logo_img = Paragraph('', ss['InvSubtitle'])

    header_table = Table(
        [[
            [Paragraph('<b>TAX INVOICE</b>', ss['InvTitle']),
             Paragraph('ORIGINAL FOR RECIPIENT', ss['SmallMuted'])],
            logo_img
        ]],
        colWidths=[usable_width * 0.6, usable_width * 0.4],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 2*mm))

    # ── Platform / Vendor Details ────────────────────────────────────────
    vendor = order.vendor
    if vendor:
        vendor_lines = [
            Paragraph(f'<b>{vendor.business_name}</b>', ss['ValueBold']),
        ]
        if vendor.gst_number:
            vendor_lines.append(Paragraph(f'GSTIN: {vendor.gst_number}', ss['ValueStyle']))
        addr_parts = [p for p in [vendor.address, vendor.city, vendor.state, vendor.pincode] if p]
        if addr_parts:
            vendor_lines.append(Paragraph(', '.join(addr_parts), ss['ValueStyle']))
        contact_parts = []
        if vendor.contact_phone:
            contact_parts.append(f'Mobile: {vendor.contact_phone}')
        if vendor.contact_email:
            contact_parts.append(f'Email: {vendor.contact_email}')
        if contact_parts:
            vendor_lines.append(Paragraph('  |  '.join(contact_parts), ss['SmallMuted']))

        for p in vendor_lines:
            elements.append(p)

    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GREY))
    elements.append(Spacer(1, 3*mm))

    # ── Invoice metadata row ─────────────────────────────────────────────
    inv_date = order.created_at.strftime('%d %b %Y')
    meta_data = [
        [Paragraph('<b>Invoice #:</b>', ss['LabelStyle']),
         Paragraph(f'{order.order_number}', ss['ValueBold']),
         Paragraph('<b>Invoice Date:</b>', ss['LabelStyle']),
         Paragraph(inv_date, ss['ValueStyle']),],
    ]
    meta_table = Table(meta_data, colWidths=[usable_width*0.18, usable_width*0.32,
                                              usable_width*0.18, usable_width*0.32])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 4*mm))

    # ── Three-column: Parent / Student / School ──────────────────────────
    student_profile = order.student_profile
    parent = student_profile.parent if student_profile else None
    school = order.school

    col_width = usable_width / 3

    # Parent details
    parent_block = [Paragraph('<b>Parent / Guardian Details:</b>', ss['LabelStyle'])]
    if parent:
        parent_block.append(Paragraph(f'{parent.full_name}', ss['ValueBold']))
        if parent.phone:
            parent_block.append(Paragraph(f'Ph: {parent.phone}', ss['ValueStyle']))
        if parent.email:
            parent_block.append(Paragraph(f'{parent.email}', ss['SmallMuted']))
    else:
        parent_block.append(Paragraph('N/A', ss['ValueStyle']))

    # Student details
    student_block = [Paragraph('<b>Student Details:</b>', ss['LabelStyle'])]
    if student_profile:
        student_block.append(Paragraph(f'{student_profile.student_name}', ss['ValueBold']))
        class_info = student_profile.class_name
        if student_profile.section:
            class_info += f' - {student_profile.section}'
        student_block.append(Paragraph(f'Class: {class_info}', ss['ValueStyle']))
        if student_profile.roll_number:
            student_block.append(Paragraph(f'Roll No: {student_profile.roll_number}', ss['ValueStyle']))
    else:
        student_block.append(Paragraph('N/A', ss['ValueStyle']))

    # School details
    school_block = [Paragraph('<b>School (Ship To):</b>', ss['LabelStyle'])]
    if school:
        school_block.append(Paragraph(f'{school.name}', ss['ValueBold']))
        addr_parts = [p for p in [school.address, school.city, school.state, school.pincode] if p]
        if addr_parts:
            school_block.append(Paragraph(', '.join(addr_parts), ss['ValueStyle']))
        if school.contact_phone:
            school_block.append(Paragraph(f'Ph: {school.contact_phone}', ss['SmallMuted']))
    else:
        school_block.append(Paragraph('N/A', ss['ValueStyle']))

    info_table = Table(
        [[parent_block, student_block, school_block]],
        colWidths=[col_width, col_width, col_width],
    )
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (0,-1), 0),
        ('RIGHTPADDING', (-1,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    # ── Items Table ──────────────────────────────────────────────────────
    items = list(order.items.all())
    col_widths_items = [
        usable_width * 0.06,   # #
        usable_width * 0.44,   # Item
        usable_width * 0.15,   # Rate/Item
        usable_width * 0.08,   # Qty
        usable_width * 0.12,   # Taxable
        usable_width * 0.15,   # Amount
    ]

    header_row = [
        Paragraph('#', ss['CenterBold']),
        Paragraph('Item', ss['CenterBold']),
        Paragraph('Rate/Item', ss['CenterBold']),
        Paragraph('Qty', ss['CenterBold']),
        Paragraph('Taxable Value', ss['CenterBold']),
        Paragraph('Amount', ss['CenterBold']),
    ]

    table_data = [header_row]
    total_qty = 0
    for idx, item in enumerate(items, 1):
        line_total = item.unit_price * item.quantity
        total_qty += item.quantity

        desc_parts = [f'<b>{item.product_name}</b>']
        variant_parts = []
        if item.size:
            variant_parts.append(f'Size: {item.size}')
        if item.color:
            variant_parts.append(f'Color: {item.color}')
        if variant_parts:
            desc_parts.append(f'<font size="7" color="#64748b">{" | ".join(variant_parts)}</font>')

        table_data.append([
            Paragraph(str(idx), ss['ValueStyle']),
            Paragraph('<br/>'.join(desc_parts), ss['ValueStyle']),
            Paragraph(f'₹{item.unit_price:,.2f}', ss['RightAligned']),
            Paragraph(str(item.quantity), ss['CenterBold']),
            Paragraph(f'₹{line_total:,.2f}', ss['RightAligned']),
            Paragraph(f'₹{line_total:,.2f}', ss['RightAligned']),
        ])

    items_table = Table(table_data, colWidths=col_widths_items, repeatRows=1)

    # Style the items table
    item_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), HEADER_TEXT),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),     # # col
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),       # Rate
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),       # Qty
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),       # Taxable + Amount
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]
    # Alternate row colours
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            item_styles.append(('BACKGROUND', (0, i), (-1, i), ROW_ALT))

    items_table.setStyle(TableStyle(item_styles))
    elements.append(items_table)

    # ── Items summary row ────────────────────────────────────────────────
    total_items_count = len(items)
    summary_text = f'Total Items: {total_items_count}  |  Qty: {total_qty}'
    elements.append(Spacer(1, 1*mm))
    elements.append(Paragraph(summary_text, ss['SmallMuted']))
    elements.append(Spacer(1, 4*mm))

    # ── Totals section ───────────────────────────────────────────────────
    subtotal = float(order.subtotal)
    tax = float(order.tax_amount)
    shipping = float(order.shipping_amount)
    discount = float(order.discount_amount)
    total = float(order.total_amount)

    totals_data = []
    totals_data.append([
        '', Paragraph('Subtotal', ss['RightAligned']),
        Paragraph(f'₹{subtotal:,.2f}', ss['RightBold']),
    ])
    if tax > 0:
        totals_data.append([
            '', Paragraph('Tax', ss['RightAligned']),
            Paragraph(f'₹{tax:,.2f}', ss['RightAligned']),
        ])
    if shipping > 0:
        totals_data.append([
            '', Paragraph('Shipping', ss['RightAligned']),
            Paragraph(f'₹{shipping:,.2f}', ss['RightAligned']),
        ])
    if discount > 0:
        totals_data.append([
            '', Paragraph('Discount', ss['RightAligned']),
            Paragraph(f'-₹{discount:,.2f}', ss['RightAligned']),
        ])
    totals_data.append([
        '', Paragraph('<b>Total</b>', ss['TotalLabel']),
        Paragraph(f'<b>₹{total:,.2f}</b>', ss['TotalValue']),
    ])

    totals_table = Table(
        totals_data,
        colWidths=[usable_width * 0.55, usable_width * 0.25, usable_width * 0.20],
    )
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (1, -1), (-1, -1), 1, BRAND_BLUE),
        ('TOPPADDING', (0, -1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(totals_table)

    # Amount in words
    elements.append(Spacer(1, 2*mm))
    words = _amount_in_words(Decimal(str(total)))
    elements.append(Paragraph(f'<i>Amount in words: {words}</i>', ss['SmallMuted']))
    elements.append(Spacer(1, 6*mm))

    # ── Payment info ─────────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GREY))
    elements.append(Spacer(1, 3*mm))

    pay_method = order.get_payment_method_display() if hasattr(order, 'get_payment_method_display') else order.payment_method
    pay_status = order.get_payment_status_display() if hasattr(order, 'get_payment_status_display') else order.payment_status
    elements.append(Paragraph(f'<b>Payment Method:</b> {pay_method}  |  <b>Payment Status:</b> {pay_status}', ss['ValueStyle']))
    elements.append(Spacer(1, 4*mm))

    # ── Authorised Signatory + T&C ───────────────────────────────────────
    vendor_name = vendor.business_name if vendor else 'eSchoolKart'

    signatory_block = [
        Paragraph(f'For <b>{vendor_name}</b>', ss['ValueBold']),
        Spacer(1, 12*mm),
        Paragraph('Authorised Signatory', ss['SmallMuted']),
    ]

    tc_block = [
        Paragraph('<b>Terms and Conditions:</b>', ss['LabelStyle']),
        Paragraph('1. All disputes are subject to the jurisdiction of the vendor\'s city.', ss['Footer']),
        Paragraph('2. Goods once sold can be exchanged within 7 days of distribution.', ss['Footer']),
        Paragraph('3. Exchange is subject to product availability and school verification.', ss['Footer']),
        Paragraph('4. This is a computer-generated invoice; no signature is required.', ss['Footer']),
    ]

    footer_table = Table(
        [[tc_block, signatory_block]],
        colWidths=[usable_width * 0.6, usable_width * 0.4],
    )
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(footer_table)

    # ── Page footer ──────────────────────────────────────────────────────
    elements.append(Spacer(1, 6*mm))
    elements.append(HRFlowable(width='100%', thickness=0.3, color=BORDER_GREY))
    elements.append(Paragraph(
        'This invoice was generated by <b>eSchoolKart.com</b> — School Uniforms & Stationery Delivered to School',
        ss['Footer'],
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ─── Delivery Slip PDF ────────────────────────────────────────────────────────

def generate_delivery_slip_pdf(order) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=25*mm, leftMargin=25*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    ss = _styles()
    elements = []
    usable_width = PAGE_W - 50*mm

    # ── Header ───────────────────────────────────────────────────────────
    logo_file = _logo_path()
    if logo_file:
        try:
            logo_img = Image(logo_file, width=40*mm, height=16*mm)
            logo_img.hAlign = 'RIGHT'
        except Exception:
            logo_img = Paragraph('', ss['InvSubtitle'])
    else:
        logo_img = Paragraph('', ss['InvSubtitle'])

    header_table = Table(
        [[
            [Paragraph('<b>DELIVERY SLIP</b>', ss['InvTitle']),
             Paragraph(f'Order: {order.order_number}', ss['ValueBold']),
             Paragraph(f'Date: {order.created_at.strftime("%d %b %Y")}', ss['ValueStyle'])],
            logo_img
        ]],
        colWidths=[usable_width * 0.6, usable_width * 0.4],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GREY))
    elements.append(Spacer(1, 4*mm))

    # ── From / To ────────────────────────────────────────────────────────
    vendor = order.vendor
    school = order.school
    student_profile = order.student_profile

    from_block = [Paragraph('<b>FROM (Vendor):</b>', ss['LabelStyle'])]
    if vendor:
        from_block.append(Paragraph(f'{vendor.business_name}', ss['ValueBold']))
        addr_parts = [p for p in [vendor.address, vendor.city, vendor.state, vendor.pincode] if p]
        if addr_parts:
            from_block.append(Paragraph(', '.join(addr_parts), ss['ValueStyle']))
        if vendor.contact_phone:
            from_block.append(Paragraph(f'Ph: {vendor.contact_phone}', ss['SmallMuted']))

    to_block = [Paragraph('<b>SHIP TO (School):</b>', ss['LabelStyle'])]
    if school:
        to_block.append(Paragraph(f'{school.name}', ss['ValueBold']))
        addr_parts = [p for p in [school.address, school.city, school.state, school.pincode] if p]
        if addr_parts:
            to_block.append(Paragraph(', '.join(addr_parts), ss['ValueStyle']))
        if school.contact_phone:
            to_block.append(Paragraph(f'Ph: {school.contact_phone}', ss['SmallMuted']))

    addr_table = Table(
        [[from_block, to_block]],
        colWidths=[usable_width * 0.5, usable_width * 0.5],
    )
    addr_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
    ]))
    elements.append(addr_table)
    elements.append(Spacer(1, 3*mm))

    # Student info
    if student_profile:
        parent = student_profile.parent
        student_info = f'<b>Student:</b> {student_profile.student_name}'
        class_info = student_profile.class_name
        if student_profile.section:
            class_info += f' - {student_profile.section}'
        student_info += f'  |  <b>Class:</b> {class_info}'
        if student_profile.roll_number:
            student_info += f'  |  <b>Roll:</b> {student_profile.roll_number}'
        if parent:
            student_info += f'  |  <b>Parent:</b> {parent.full_name}'
        elements.append(Paragraph(student_info, ss['ValueStyle']))
    elements.append(Spacer(1, 4*mm))

    # ── Items Table (No Prices) ──────────────────────────────────────────
    col_widths = [
        usable_width * 0.08,
        usable_width * 0.52,
        usable_width * 0.15,
        usable_width * 0.12,
        usable_width * 0.13,
    ]

    header_row = [
        Paragraph('#', ss['CenterBold']),
        Paragraph('Product', ss['CenterBold']),
        Paragraph('Size', ss['CenterBold']),
        Paragraph('Color', ss['CenterBold']),
        Paragraph('Qty', ss['CenterBold']),
    ]

    table_data = [header_row]
    for idx, item in enumerate(order.items.all(), 1):
        table_data.append([
            Paragraph(str(idx), ss['ValueStyle']),
            Paragraph(f'<b>{item.product_name}</b>', ss['ValueStyle']),
            Paragraph(item.size, ss['ValueStyle']),
            Paragraph(item.color or '—', ss['ValueStyle']),
            Paragraph(str(item.quantity), ss['CenterBold']),
        ])

    slip_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    slip_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), HEADER_TEXT),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            slip_styles.append(('BACKGROUND', (0, i), (-1, i), ROW_ALT))

    slip_table.setStyle(TableStyle(slip_styles))
    elements.append(slip_table)

    # ── Receiver acknowledgement ─────────────────────────────────────────
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph('<b>Received by:</b> ____________________________', ss['ValueStyle']))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph('<b>Date:</b> ____________________________', ss['ValueStyle']))
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width='100%', thickness=0.3, color=BORDER_GREY))
    elements.append(Paragraph(
        'Generated by <b>eSchoolKart.com</b> — School Uniforms & Stationery Delivered to School',
        ss['Footer'],
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
