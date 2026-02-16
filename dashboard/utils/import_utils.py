import pandas as pd
from django.db import transaction
from django.db.models import ForeignKey

def process_import(model, file):
    try:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()
        records = df.to_dict('records')
        
        created_count = 0
        errors = []
        model_fields = {f.name: f for f in model._meta.get_fields()}
        
        try:
            with transaction.atomic():
                for index, record in enumerate(records):
                    row_num = index + 2 # 1-based, plus header
                    try:
                        # Clean NaN
                        clean_record = {k: v for k, v in record.items() if pd.notna(v)}
                        
                        instance_data = {}
                        # Case-insensitive column matching
                        df_columns_map = {col.lower(): col for col in df.columns}
                        
                        instance_data = {}
                        for field_name, field in model_fields.items():
                            if field.primary_key: continue # Skip ID if auto-generated, unless explicitly provided
                            
                            # Try to find the column in Excel
                            excel_col = df_columns_map.get(field_name.lower())
                            if not excel_col:
                                # Start of specific logic for required fields
                                if not field.null and not field.blank and field.default == models.NOT_PROVIDED:
                                     # If required and missing, we might fail unless it's a specific case
                                     continue 
                                continue

                            value = record.get(excel_col)
                            if pd.isna(value): continue

                            if isinstance(field, ForeignKey):
                                # ... (Existing FK logic) ...
                                related_model = field.related_model
                                related_obj = None
                                try:
                                    if hasattr(related_model, 'name'):
                                        related_obj = related_model.objects.filter(name__iexact=str(value)).first()
                                    elif hasattr(related_model, 'title'):
                                        related_obj = related_model.objects.filter(title__iexact=str(value)).first()
                                    elif hasattr(related_model, 'username'):
                                        related_obj = related_model.objects.filter(username__iexact=str(value)).first()
                                    else:
                                        related_obj = related_model.objects.filter(pk=value).first()
                                except Exception:
                                    pass # will raise ValueError below if not found
                                
                                if related_obj:
                                    instance_data[field_name] = related_obj
                                else:
                                     raise ValueError(f"Related object '{value}' not found for field '{field_name}'")
                            else:
                                instance_data[field_name] = value

                        # Check for required fields before creating
                        if not instance_data:
                             raise ValueError("Row empty or no matching columns found")

                        if 'id' in instance_data:
                            obj, created = model.objects.update_or_create(id=instance_data['id'], defaults=instance_data)
                            if created: created_count += 1
                        else:
                            model.objects.create(**instance_data)
                            created_count += 1

                    except Exception as e:
                        errors.append({"row": row_num, "error": str(e)})
                
                if errors:
                    raise ValueError("Import validation failed")

        except ValueError:
            if errors:
                return 0, errors
            raise

        return created_count, []

    except Exception as e:
        raise e
