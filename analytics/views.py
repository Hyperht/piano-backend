from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from analytics.selectors.customers import get_top_customers_summary

class TopCustomersAPIView(APIView):

    def get(self, request):
        range_filter = request.GET.get("range", "30d")
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

        data = get_top_customers_summary(
            start_date=start_date,
            end_date=end_date
        )

        return Response(data)
