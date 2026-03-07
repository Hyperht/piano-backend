import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from django.apps import apps
from dashboard.utils.import_utils import process_import

logger = logging.getLogger(__name__)

# Whitelist of models allowed for import, mapping model name -> app label
IMPORT_MODEL_WHITELIST = {
    'Product': 'products',
    'Category': 'products',
    'Subcategory': 'products',
    'Color': 'products',
    'Room': 'products',
    'Style': 'products',
    'CustomUser': 'users',
    'Vendor': 'vendors',
    'Governorate': 'users',
    'Area': 'users',
    'Coupon': 'marketing',
    'Order': 'orders',
    'StockMovement': 'inventory',
}


class ImportDataView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, model_name):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        app_label = IMPORT_MODEL_WHITELIST.get(model_name)
        if not app_label:
            logger.warning(f"Import rejected: model '{model_name}' not in whitelist. User: {request.user}")
            return Response(
                {'error': f'Model {model_name} is not allowed for import'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return Response({'error': f'Model {model_name} not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            logger.info(f"Import started: model={model_name}, file={file.name}, user={request.user}")
            count, errors = process_import(model, file)

            if errors:
                logger.warning(f"Import validation failed: {len(errors)} errors for {model_name}")
                return Response({'error': 'Validation failed', 'details': errors}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Import successful: {count} records created for {model_name}")
            return Response({'message': f'Successfully imported {count} records'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Import failed for {model_name}: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

