import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.utils import timezone
from django.http import FileResponse

def generate_excel_report(analytics):
    output = BytesIO()
    
    # Create DataFrames
    summary_data = [{
        'Metric': 'Total Revenue', 'Value': analytics['total_revenue']
    }, {
        'Metric': 'Total Orders (Year)', 'Value': analytics['orders_metrics']['last_year']
    }, {
        'Metric': 'Orders (30 Days)', 'Value': analytics['orders_metrics']['last_30_days']
    }]
    df_summary = pd.DataFrame(summary_data)
    df_products = pd.DataFrame(analytics['top_selling'])
    df_orders = pd.DataFrame(analytics['recent_orders'])
    
    # Remove timezones for Excel compatibility
    for df in [df_summary, df_products, df_orders]:
        for col in df.select_dtypes(include=['datetime64[ns, UTC]', 'datetimetz']).columns:
            df[col] = df[col].dt.tz_localize(None)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary.to_excel(writer, index=False, sheet_name='Summary')
        if not df_products.empty:
            df_products.to_excel(writer, index=False, sheet_name='Top Products')
        if not df_orders.empty:
            df_orders.to_excel(writer, index=False, sheet_name='Recent Orders')
    
    output.seek(0)
    output.seek(0)
    response = FileResponse(output, as_attachment=True, filename=f'analytics_{timezone.now().date()}.xlsx')
    return response

def generate_pdf_report(analytics):
    output = BytesIO()
    p = canvas.Canvas(output, pagesize=letter)
    p.setTitle("Analytics Report")
    
    # Header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, 750, "Dashboard Analytics Report")
    p.setFont("Helvetica", 12)
    p.drawString(50, 730, f"Date: {timezone.now().date()}")
    
    # Summary
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 700, "Summary")
    p.setFont("Helvetica", 12)
    p.drawString(70, 680, f"Total Revenue: ${analytics['total_revenue']}")
    p.drawString(70, 660, f"Total Orders (Last Year): {analytics['orders_metrics']['last_year']}")
    
    # Top Products
    y = 620
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Top Selling Products")
    y -= 25
    p.setFont("Helvetica", 12)
    
    for item in analytics['top_selling']:
        text = f"- {item['name']}: {item['sales_count']} sold (${item['revenue']})"
        p.drawString(70, y, text)
        y -= 20
        
    # Recent Orders
    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Recent Orders")
    y -= 25
    p.setFont("Helvetica", 12)
    
    for order in analytics['recent_orders']:
        text = f"Order #{order['id']} - {order['status']} - ${order['final_total']}"
        p.drawString(70, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = 750

    p.save()
    output.seek(0)
    output.seek(0)
    response = FileResponse(output, as_attachment=True, filename=f'analytics_{timezone.now().date()}.pdf')
    return response
