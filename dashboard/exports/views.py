from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from dashboard.utils.export_utils import generate_excel_report, generate_pdf_report
from dashboard.analytics.services import DashboardService

class ExportAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        export_type = request.query_params.get('type', 'excel')
        analytics = DashboardService.get_aggregated_analytics()
        
        if export_type == 'pdf':
            return generate_pdf_report(analytics)
        else:
            return generate_excel_report(analytics)
