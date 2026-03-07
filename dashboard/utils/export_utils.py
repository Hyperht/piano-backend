import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from django.utils import timezone
from django.http import FileResponse


def _safe_str(value, default='N/A'):
    """Safely convert a value to string, replacing None/empty with default."""
    if value is None or value == '':
        return default
    return str(value)


def generate_excel_report(analytics):
    output = BytesIO()

    # Section 1: Summary
    summary_data = [
        {'Metric': 'Total Revenue', 'Value': analytics.get('total_revenue', 0)},
        {'Metric': 'Total Orders', 'Value': analytics.get('total_orders', 0)},
        {'Metric': 'Total Users', 'Value': analytics.get('total_users', 0)},
    ]
    df_summary = pd.DataFrame(summary_data)

    # Section 2: Top Selling Products
    top_selling = analytics.get('top_selling', [])
    df_products = pd.DataFrame([
        {
            'Product': item.get('name', ''),
            'Units Sold': item.get('sales_count', 0),
            'Revenue': item.get('revenue', 0),
        }
        for item in top_selling
    ]) if top_selling else pd.DataFrame()

    # Section 3: Recent Orders
    recent_orders = analytics.get('recent_orders', [])
    df_orders = pd.DataFrame([
        {
            'Order ID': o.get('id', ''),
            'Status': o.get('status', ''),
            'Total Amount': o.get('total_amount', o.get('final_total', 0)),
            'User Email': o.get('user', {}).get('email', '') if isinstance(o.get('user'), dict) else o.get('user_email', ''),
            'User Name': o.get('user', {}).get('full_name', '') if isinstance(o.get('user'), dict) else '',
            'Phone 1': o.get('shipping_address', {}).get('phone_number_1', '') if isinstance(o.get('shipping_address'), dict) else '',
            'City': o.get('shipping_address', {}).get('area_name', '') if isinstance(o.get('shipping_address'), dict) else '',
            'Date': o.get('created_at', ''),
        }
        for o in recent_orders
    ]) if recent_orders else pd.DataFrame()

    # Section 4: Top Customers
    top_customers = analytics.get('top_customers', [])
    df_customers = pd.DataFrame([
        {
            'Email': c.get('email', ''),
            'Name': f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or 'N/A',
            'Total Spent': c.get('total_spent', 0),
            'Total Orders': c.get('total_orders', 0),
        }
        for c in top_customers
    ]) if top_customers else pd.DataFrame()

    # Section 5: Stock Needed
    stock_needed = analytics.get('stock_needed', [])
    df_stock = pd.DataFrame([
        {
            'Product': item.get('name', ''),
            'Category': item.get('category', ''),
            'Quantity': item.get('quantity', 0),
        }
        for item in stock_needed
    ]) if stock_needed else pd.DataFrame()

    # Section 6: Top Coupons
    top_coupons = analytics.get('top_coupons', [])
    df_coupons = pd.DataFrame([
        {
            'Coupon Code': item.get('code', ''),
            'Discount': item.get('discount_value', 0),
            'Used Count': item.get('usage_count', 0),
            'Total Generated': item.get('revenue_generated', 0),
        }
        for item in top_coupons
    ]) if top_coupons else pd.DataFrame()
    
    # Section 7: Revenue Analysis
    revenue_chart = analytics.get('revenue_chart', [])
    df_revenue = pd.DataFrame([
        {
            'Date': item.get('date', ''),
            'Revenue': item.get('revenue', 0),
        }
        for item in revenue_chart
    ]) if revenue_chart else pd.DataFrame()

    # Remove timezone info for Excel compatibility
    for df in [df_summary, df_products, df_orders, df_customers, df_stock, df_coupons, df_revenue]:
        for col in df.select_dtypes(include=['datetime64[ns, UTC]', 'datetimetz']).columns:
            df[col] = df[col].dt.tz_localize(None)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        startrow = 0
        df_summary.to_excel(writer, index=False, sheet_name='Full Report', startrow=startrow)
        startrow += len(df_summary) + 2

        if not df_revenue.empty:
            pd.DataFrame([['--- Revenue Analysis ---']]).to_excel(writer, index=False, header=False, sheet_name='Full Report', startrow=startrow)
            startrow += 1
            df_revenue.to_excel(writer, index=False, sheet_name='Full Report', startrow=startrow)
            startrow += len(df_revenue) + 2

        if not df_products.empty:
            pd.DataFrame([['--- Top Products ---']]).to_excel(writer, index=False, header=False, sheet_name='Full Report', startrow=startrow)
            startrow += 1
            df_products.to_excel(writer, index=False, sheet_name='Full Report', startrow=startrow)
            startrow += len(df_products) + 2

        if not df_orders.empty:
            pd.DataFrame([['--- Recent Orders ---']]).to_excel(writer, index=False, header=False, sheet_name='Full Report', startrow=startrow)
            startrow += 1
            df_orders.to_excel(writer, index=False, sheet_name='Full Report', startrow=startrow)
            startrow += len(df_orders) + 2

        if not df_customers.empty:
            pd.DataFrame([['--- Top Customers ---']]).to_excel(writer, index=False, header=False, sheet_name='Full Report', startrow=startrow)
            startrow += 1
            df_customers.to_excel(writer, index=False, sheet_name='Full Report', startrow=startrow)
            startrow += len(df_customers) + 2

        if not df_stock.empty:
            pd.DataFrame([['--- Stock Needed ---']]).to_excel(writer, index=False, header=False, sheet_name='Full Report', startrow=startrow)
            startrow += 1
            df_stock.to_excel(writer, index=False, sheet_name='Full Report', startrow=startrow)
            startrow += len(df_stock) + 2

        if not df_coupons.empty:
            pd.DataFrame([['--- Top Coupons ---']]).to_excel(writer, index=False, header=False, sheet_name='Full Report', startrow=startrow)
            startrow += 1
            df_coupons.to_excel(writer, index=False, sheet_name='Full Report', startrow=startrow)
            startrow += len(df_coupons) + 2


    output.seek(0)
    response = FileResponse(
        output,
        as_attachment=True,
        filename=f'analytics_{timezone.now().date()}.xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    return response


def generate_pdf_report(analytics):
    output = BytesIO()
    p = canvas.Canvas(output, pagesize=letter)
    p.setTitle("Dashboard Analytics Report")
    width, height = letter

    def check_page(y, p, threshold=80):
        if y < threshold:
            p.showPage()
            p.setFont("Helvetica", 11)
            return height - 60
        return y

    # ─── Header ─────────────────────────────────────────────────────────────────
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "Piano Admin Panel — Analytics Report")
    p.setFont("Helvetica", 11)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    start_date = analytics.get('start_date')
    end_date = analytics.get('end_date')
    if start_date and end_date:
        date_str = f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    else:
        date_str = f"Date Range: Last {analytics.get('period', 30)} Days"

    p.drawString(50, height - 70, f"{date_str} (Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')})")
    p.setFillColorRGB(0, 0, 0)
    p.line(50, height - 80, width - 50, height - 80)

    y = height - 105

    # ─── Section 1: Summary ──────────────────────────────────────────────────────
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "--- Summary ---")
    y -= 22
    p.setFont("Helvetica", 11)

    total_revenue = analytics.get('total_revenue', 0)
    
    summary_items = [
        ("Total Revenue", f"${float(total_revenue):,.2f}"),
        ("Total Orders", str(analytics.get('total_orders', 0))),
        ("Active Users", str(analytics.get('active_users', 0))),
    ]
    for label, value in summary_items:
        p.setFont("Helvetica-Bold", 11)
        p.drawString(70, y, f"{label}:")
        p.setFont("Helvetica", 11)
        p.drawString(200, y, value)
        y -= 18

    y -= 15

    # ─── Section 1.5: Revenue Analysis ───────────────────────────────────────────
    revenue_chart = analytics.get('revenue_chart', [])
    if revenue_chart:
        y = check_page(y, p)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "--- Daily Revenue Trend ---")
        y -= 22
        
        p.setFont("Helvetica-Bold", 9)
        rev_headers = ["Date", "Revenue"]
        rev_col_x = [50, 200]
        for i, h in enumerate(rev_headers):
            p.drawString(rev_col_x[i], y, h)
        y -= 3
        p.line(50, y, width - 50, y)
        y -= 12

        p.setFont("Helvetica", 9)
        for item in revenue_chart:
            y = check_page(y, p)
            row = [
                _safe_str(item.get('date', '')),
                f"${float(item.get('revenue', 0)):.2f}",
            ]
            for i, cell in enumerate(row):
                p.drawString(rev_col_x[i], y, cell)
            y -= 14

        y -= 15


    # ─── Section 2: Top Products ─────────────────────────────────────────
    y = check_page(y, p)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "--- Top Products ---")
    y -= 22

    p.setFont("Helvetica-Bold", 9)
    prod_headers = ["Product", "Units Sold", "Revenue"]
    prod_col_x = [50, 340, 430]
    for i, h in enumerate(prod_headers):
        p.drawString(prod_col_x[i], y, h)
    y -= 3
    p.line(50, y, width - 50, y)
    y -= 12

    p.setFont("Helvetica", 9)
    for item in analytics.get('top_selling', []):
        y = check_page(y, p)
        rev = item.get('revenue') or 0
        units = item.get('sales_count') or item.get('units_sold') or 0
        row = [
            _safe_str(item.get('name', item.get('product__name', '')))[:45],
            str(units),
            f"${float(rev):.2f}",
        ]
        for i, cell in enumerate(row):
            p.drawString(prod_col_x[i], y, cell)
        y -= 14

    y -= 15

    # ─── Section 3: Top Customers ────────────────────────────────────────────────
    y = check_page(y, p)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "--- Top Customers ---")
    y -= 22

    p.setFont("Helvetica-Bold", 9)
    cust_headers = ["Name", "Email", "Total Spent", "Orders"]
    cust_col_x = [50, 200, 370, 450]
    for i, h in enumerate(cust_headers):
        p.drawString(cust_col_x[i], y, h)
    y -= 3
    p.line(50, y, width - 50, y)
    y -= 12

    p.setFont("Helvetica", 9)
    for c in analytics.get('top_customers', []):
        y = check_page(y, p)
        name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or 'N/A'
        row = [
            name[:25],
            _safe_str(c.get('email', ''))[:30],
            f"${c.get('total_spent', 0)}",
            str(c.get('total_orders', 0)),
        ]
        for i, cell in enumerate(row):
            p.drawString(cust_col_x[i], y, cell)
        y -= 14

    y -= 15
    
    # ─── Section 4: Recent Orders ────────────────────────────────────────────────
    y = check_page(y, p)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "--- Recent Orders ---")
    y -= 22

    p.setFont("Helvetica-Bold", 9)
    headers = ["Order ID", "Status", "Amount", "User Email", "City"]
    col_x = [50, 115, 195, 275, 420]
    for i, h in enumerate(headers):
        p.drawString(col_x[i], y, h)
    y -= 3
    p.line(50, y, width - 50, y)
    y -= 12

    p.setFont("Helvetica", 9)
    for order in analytics.get('recent_orders', []):
        y = check_page(y, p)
        user_data = order.get('user', {}) if isinstance(order.get('user'), dict) else {}
        shipping_data = order.get('shipping_address', {}) if isinstance(order.get('shipping_address'), dict) else {}
        
        row = [
            _safe_str(order.get('id')),
            _safe_str(order.get('status')),
            f"${order.get('total_amount', order.get('final_total', 0))}",
            _safe_str(user_data.get('email', order.get('user_email', '')))[:30],
            _safe_str(shipping_data.get('area_name', '')),
        ]
        for i, cell in enumerate(row):
            p.drawString(col_x[i], y, cell)
        y -= 14

    y -= 15

    # ─── Section 5: Stock Needed ─────────────────────────────────────────────────
    y = check_page(y, p)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "--- Stock Needed ---")
    y -= 22

    p.setFont("Helvetica-Bold", 9)
    stock_headers = ["Product", "Category", "Quantity"]
    stock_col_x = [50, 250, 450]
    for i, h in enumerate(stock_headers):
        p.drawString(stock_col_x[i], y, h)
    y -= 3
    p.line(50, y, width - 50, y)
    y -= 12

    p.setFont("Helvetica", 9)
    for item in analytics.get('stock_needed', []):
        y = check_page(y, p)
        row = [
            _safe_str(item.get('name', ''))[:40],
            _safe_str(item.get('category', ''))[:30],
            str(item.get('quantity', 0)),
        ]
        for i, cell in enumerate(row):
            p.drawString(stock_col_x[i], y, cell)
        y -= 14

    y -= 15

    # ─── Section 6: Top Coupons ──────────────────────────────────────────────────
    y = check_page(y, p)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "--- Top Coupons ---")
    y -= 22

    p.setFont("Helvetica-Bold", 9)
    cpn_headers = ["Coupon Code", "Discount", "Used Count", "Total Generated"]
    cpn_col_x = [50, 180, 280, 400]
    for i, h in enumerate(cpn_headers):
        p.drawString(cpn_col_x[i], y, h)
    y -= 3
    p.line(50, y, width - 50, y)
    y -= 12

    p.setFont("Helvetica", 9)
    for item in analytics.get('top_coupons', []):
        y = check_page(y, p)
        disc = float(item.get('discount_value', 0) or 0)
        row = [
            _safe_str(item.get('code', '')),
            f"{disc:.2f}",
            str(item.get('usage_count', 0)),
            f"${float(item.get('revenue_generated', 0) or 0):.2f}",
        ]
        for i, cell in enumerate(row):
            p.drawString(cpn_col_x[i], y, cell)
        y -= 14

    p.save()
    output.seek(0)

    response = FileResponse(
        output,
        as_attachment=True,
        filename=f'analytics_{timezone.now().date()}.pdf',
        content_type='application/pdf'
    )
    return response
