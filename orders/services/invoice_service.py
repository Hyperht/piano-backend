from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from orders.models import Order

class InvoiceService:
    @staticmethod
    def generate_invoice_pdf(order: Order) -> bytes:
        """
        Generates a PDF invoice summarizing the order.
        Strictly uses snapshotted fields from Order and OrderItem without recalculation.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Header
        elements.append(Paragraph(f"Invoice for Order #{order.id}", styles['Title']))
        elements.append(Spacer(1, 12))
        
        # Order Info
        customer_name = order.user.get_full_name() if order.user else 'Guest'
        elements.append(Paragraph(f"<b>Customer:</b> {customer_name}", styles['Normal']))
        elements.append(Paragraph(f"<b>Date:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"<b>Status:</b> {order.get_status_display()}", styles['Normal']))
        elements.append(Spacer(1, 24))
        
        # Items Table
        data = [['Product', 'Vendor', 'Qty', 'Price', 'Subtotal']]
        for item in order.items.select_related('product', 'vendor'):
            product_name = item.product.name if item.product else 'Deleted Product'
            vendor_name = item.vendor.name if item.vendor else 'N/A'
            data.append([
                product_name,
                vendor_name,
                str(item.quantity),
                f"${item.price_snapshot:,.2f}",
                f"${item.subtotal:,.2f}"
            ])
            
        table = Table(data, colWidths=[200, 100, 50, 75, 75])
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
        elements.append(Spacer(1, 24))
        
        # Totals
        elements.append(Paragraph(f"<b>Subtotal:</b> ${order.cart_subtotal:,.2f}", styles['Normal']))
        elements.append(Paragraph(f"<b>Shipping:</b> ${order.shipping_cost:,.2f}", styles['Normal']))
        elements.append(Paragraph(f"<b>Discount:</b> -${order.coupon_discount:,.2f}", styles['Normal']))
        elements.append(Paragraph(f"<b>Total:</b> ${order.final_total:,.2f}", styles['Heading3']))
        
        doc.build(elements)
        return buffer.getvalue()
