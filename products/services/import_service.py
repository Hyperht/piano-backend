import pandas as pd
from io import BytesIO
from django.db import transaction
from products.services.product_service import ProductService
from vendors.models import Vendor
from rest_framework.exceptions import ValidationError

class ImportService:
    @staticmethod
    def import_products_from_excel(excel_file, vendor: Vendor) -> dict:
        """
        Validates and imports products from an Excel file.
        Uses transaction batching and collects structured errors.
        Returns a dict with 'success_count', 'error_count', and 'error_file' (bytes if errors exist).
        """
        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            raise ValidationError(f"Invalid Excel file: {str(e)}")
            
        required_columns = ['Name', 'Original Price', 'Quantity', 'Category Slug']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValidationError(f"Missing required columns: {', '.join(missing_cols)}")
            
        success_count = 0
        errors = []
        
        for index, row in df.iterrows():
            row_num = index + 2  # +2 accounts for 0-index and header row
            try:
                data = {
                    'name': str(row.get('Name')),
                    'original_price': float(row.get('Original Price', 0)),
                    'quantity': int(row.get('Quantity', 0)),
                }
                
                from products.models import Category
                cat_slug = str(row.get('Category Slug'))
                try:
                    category = Category.objects.get(slug=cat_slug)
                    data['category'] = category
                except Category.DoesNotExist:
                    raise ValueError(f"Category with slug '{cat_slug}' not found.")
                
                data['vendor'] = vendor
                
                # Use sub-transaction to allow partial failures without rollback of entire batch
                with transaction.atomic():
                    ProductService.create_product(data)
                    
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'Row Number': row_num,
                    'Field': 'Multiple',
                    'Error Message': str(e)
                })
                
        result = {
            'success_count': success_count,
            'error_count': len(errors),
            'error_file': None
        }
        
        if errors:
            error_df = pd.DataFrame(errors)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                error_df.to_excel(writer, index=False, sheet_name='Errors')
            result['error_file'] = output.getvalue()
            
        return result
