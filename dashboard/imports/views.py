from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from django.apps import apps
from dashboard.utils.import_utils import process_import

class ImportDataView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, model_name):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            try:
                model = apps.get_model('users', model_name)
            except LookupError:
                return Response({'error': f'Model {model_name} not found'}, status=status.HTTP_404_NOT_FOUND)

            count, errors = process_import(model, file)
            
            if errors:
                return Response({'error': 'Validation failed', 'details': errors}, status=status.HTTP_400_BAD_REQUEST)
                
            return Response({'message': f'Successfully imported {count} records'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
