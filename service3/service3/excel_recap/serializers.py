# from rest_framework import serializers
# from .models import ExcelUpload, BudgetRecord

# class BudgetRecordSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = BudgetRecord
#         fields = '__all__'

# class ExcelUploadSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ExcelUpload
#         fields = ['id', 'file_name', 'uploaded_at', 'status']

# class ExcelFileSerializer(serializers.Serializer):
#     file = serializers.FileField()
from rest_framework import serializers
from .models import ExcelUpload, BudgetRecord
from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, get_famille_nom


class BudgetRecordSerializer(serializers.ModelSerializer):

    # 🔥 champs calculés
    region_nom = serializers.SerializerMethodField()
    activite_nom = serializers.SerializerMethodField()
    famille_nom = serializers.SerializerMethodField()

    class Meta:
        model = BudgetRecord
        fields = '__all__'  # garde tout + champs ajoutés automatiquement

    # ─────────────────────────
    # MAPPINGS
    # ─────────────────────────

    def get_region_nom(self, obj):
        code = str(obj.region or '').strip()
        return REGION_MAPPING.get(code, code)

    def get_activite_nom(self, obj):
        code = str(obj.activite or '').strip()
        return ACTIVITE_MAPPING.get(code, code)

    def get_famille_nom(self, obj):
        code = str(obj.famille or '').strip()
        return get_famille_nom(code)


class ExcelUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcelUpload
        fields = ['id', 'file_name', 'uploaded_at', 'status']


class ExcelFileSerializer(serializers.Serializer):
    file = serializers.FileField()