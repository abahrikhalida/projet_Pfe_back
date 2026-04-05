from django.apps import AppConfig

class ExcelRecapConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Add this line
    name = 'excel_recap'