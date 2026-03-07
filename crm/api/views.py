from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from users.models import ContactMessage
from crm.api.serializers import ContactMessageSerializer
from crm.selectors.customer_selectors import (
    get_top_customers,
    get_geographic_sales,
    get_top_customers,
    get_geographic_sales,
    get_customer_count_by_region,
    get_all_customers_with_stats,
)
from django.utils import timezone
from datetime import timedelta
import pandas as pd
from io import BytesIO
from django.http import FileResponse


class ContactMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for handling contact form submissions."""
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']


class TopCustomersAPIView(APIView):
    """
    Returns top customers ranked by total_spent.
    Admin-only endpoint. Thin view — delegates to selector.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        vendor_id = request.query_params.get('vendor_id')
        limit = int(request.query_params.get('limit', 10))
        data = get_top_customers(vendor=vendor_id, limit=limit)
        return Response(data)


class GeographicSalesAPIView(APIView):
    """
    Returns sales grouped by region snapshot.
    Admin-only endpoint. Thin view — delegates to selector.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        vendor_id = request.query_params.get('vendor_id')
        data = get_geographic_sales(vendor=vendor_id)
        return Response(data)


class CustomerRegionBreakdownAPIView(APIView):
    """
    Returns customer count by region.
    Admin-only endpoint.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = get_customer_count_by_region()
        return Response(data)


class AllCustomersAPIView(APIView):
    """
    Returns full CRM dataset for all customers (See All).
    Admin-only endpoint.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        range_filter = request.query_params.get("range", "30d")
        end_date = timezone.now()

        if range_filter == "7d":
            start_date = end_date - timedelta(days=7)
        elif range_filter == "30d":
            start_date = end_date - timedelta(days=30)
        elif range_filter == "3m":
            start_date = end_date - timedelta(days=90)
        elif range_filter == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = None

        data = get_all_customers_with_stats(
            start_date=start_date,
            end_date=end_date
        )

        return Response(list(data))


class ExportCustomersAPIView(APIView):
    """
    Exports full CRM dataset for all customers (See All) to Excel.
    Admin-only endpoint.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        range_filter = request.query_params.get("range", "30d")
        end_date = timezone.now()

        if range_filter == "7d":
            start_date = end_date - timedelta(days=7)
        elif range_filter == "30d":
            start_date = end_date - timedelta(days=30)
        elif range_filter == "3m":
            start_date = end_date - timedelta(days=90)
        elif range_filter == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = None

        data = list(get_all_customers_with_stats(
            start_date=start_date,
            end_date=end_date
        ))

        df_customers = pd.DataFrame([
            {
                'Email': c.get('user__email', ''),
                'Name': f"{c.get('user__first_name', '')} {c.get('user__last_name', '')}".strip(),
                'Phone 1': c.get('user__phone1', ''),
                'Phone 2': c.get('user__phone2', ''),
                'City': c.get('user__city', ''),
                'Address': c.get('user__address', ''),
                'Total Spent': c.get('total_spent', 0),
                'Total Orders': c.get('total_orders', 0),
                'Last Order Date': c.get('last_order', '').strftime('%Y-%m-%d %H:%M:%S') if c.get('last_order') else 'N/A',
            }
            for c in data
        ]) if data else pd.DataFrame(columns=[
            'Email', 'Name', 'Phone 1', 'Phone 2', 'City', 'Address', 'Total Spent', 'Total Orders', 'Last Order Date'
        ])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_customers.to_excel(writer, index=False, sheet_name='Customers')

        output.seek(0)
        response = FileResponse(
            output,
            as_attachment=True,
            filename=f'customers_export_{timezone.now().date()}.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        return response
