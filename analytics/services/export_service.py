import pandas as pd
from io import BytesIO
from orders.selectors.orders import get_all_orders_for_export
from django.utils.timezone import localtime

class ExportService:
    @staticmethod
    def export_sales_excel(start_date=None, end_date=None) -> bytes:
        """
        Exports sales data to an Excel file using pandas.
        Uses selectors to fetch optimized querysets without heavy ORM logic here.
        Returns the raw bytes of the Excel file.
        """
        orders = get_all_orders_for_export(start_date, end_date)
        
        data = []
        for order in orders:
            # We want one row per order item for detailed reporting
            for item in order.items.all():
                data.append({
                    "Order ID": order.id,
                    "Date": localtime(order.created_at).strftime('%Y-%m-%d %H:%M'),
                    "Status": order.get_status_display(),
                    "Customer": order.user.email if order.user else 'Guest',
                    "Vendor": item.vendor.name if item.vendor else 'System',
                    "Product": item.product.name if item.product else 'Deleted Product',
                    "Quantity": item.quantity,
                    "Price Snapshot": float(item.price_snapshot),
                    "Subtotal": float(item.subtotal),
                    "Commission": float(item.commission_amount),
                    "Order Discount": float(order.coupon_discount),
                    "Shipping": float(order.shipping_cost),
                    "Total Order Value": float(order.final_total),
                })
                
        df = pd.DataFrame(data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sales Data')
            
        return output.getvalue()
