
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import generics
# from django.db.models import Sum
# from .models import ExcelUpload, BudgetRecord
# from .serializers import ExcelUploadSerializer, BudgetRecordSerializer, ExcelFileSerializer
# from .utils import parse_excel
# from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, FAMILLE_ORDER, get_famille_nom

# # ─────────────────────────────────────────
# # CONSTANTES
# # ─────────────────────────────────────────

# NUMERIC_FIELDS = [
#     'cout_initial_total', 'cout_initial_dont_dex',
#     'realisation_cumul_n_mins1_total', 'realisation_cumul_n_mins1_dont_dex',
#     'real_s1_n_total', 'real_s1_n_dont_dex',
#     'prev_s2_n_total', 'prev_s2_n_dont_dex',
#     'prev_cloture_n_total', 'prev_cloture_n_dont_dex',
#     'prev_n_plus1_total', 'prev_n_plus1_dont_dex',
#     'reste_a_realiser_total', 'reste_a_realiser_dont_dex',
#     'prev_n_plus2_total', 'prev_n_plus2_dont_dex',
#     'prev_n_plus3_total', 'prev_n_plus3_dont_dex',
#     'prev_n_plus4_total', 'prev_n_plus4_dont_dex',
#     'prev_n_plus5_total', 'prev_n_plus5_dont_dex',
#     'janvier_total', 'fevrier_total', 'mars_total',
#     'avril_total', 'mai_total', 'juin_total',
#     'juillet_total', 'aout_total', 'septembre_total',
#     'octobre_total', 'novembre_total', 'decembre_total',
# ]

# REGION_EXCLUSIONS   = [None, '', 'Région', 'REGION', 'region', 'Total', 'TOTAL']
# FAMILLE_EXCLUSIONS  = [None, '', 'Famille', 'FAMILLE', 'famille', 'Total', 'TOTAL']
# ACTIVITE_EXCLUSIONS = [None, '', 'Activité', 'ACTIVITE', 'activite', 'Total', 'TOTAL']


# # ─────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────

# def build_aggregation():
#     return {f: Sum(f) for f in NUMERIC_FIELDS}


# def apply_mapping(data, key_field, mapping):
#     """Ajoute le nom complet pour région et activité."""
#     result = []
#     for row in data:
#         code = str(row.get(key_field, '') or '').strip()
#         row[key_field + '_code'] = code
#         row[key_field + '_nom'] = mapping.get(code, code)
#         result.append(row)
#     return result


# def group_by_famille(data):
#     """
#     Regroupe toutes les sous-familles (2.1, 2.2, 2.61...)
#     en familles principales (Maintenance Puits...).
#     Retourne seulement 7 lignes max.
#     """
#     grouped = {}

#     for row in data:
#         code = str(row.get('famille', '') or '').strip()
#         if not code:
#             continue
#         nom = get_famille_nom(code)

#         if nom not in grouped:
#             grouped[nom] = {field: 0 for field in NUMERIC_FIELDS}
#             grouped[nom]['famille_nom'] = nom

#         for field in NUMERIC_FIELDS:
#             val = row.get(field) or 0
#             grouped[nom][field] += float(val)

#     # Trier dans l'ordre logique
#     result = sorted(
#         grouped.values(),
#         key=lambda x: FAMILLE_ORDER.index(x['famille_nom'])
#         if x['famille_nom'] in FAMILLE_ORDER else 99
#     )
#     return result


# # ─────────────────────────────────────────
# # UPLOAD VIEWS
# # ─────────────────────────────────────────

# class ExcelUploadView(APIView):
#     def post(self, request):
#         serializer = ExcelFileSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=400)

#         file = serializer.validated_data['file']
#         if not file.name.endswith(('.xlsx', '.xls')):
#             return Response({'error': 'Only .xlsx or .xls files accepted.'}, status=400)

#         upload = ExcelUpload.objects.create(file_name=file.name, status='pending')
#         try:
#             count = parse_excel(file, upload)
#             upload.status = 'processed'
#             upload.save()
#             return Response(
#                 {'message': f'{count} records imported.', 'upload_id': upload.id},
#                 status=201
#             )
#         except Exception as e:
#             upload.status = 'failed'
#             upload.save()
#             return Response({'error': str(e)}, status=500)


# class UploadListView(generics.ListAPIView):
#     queryset = ExcelUpload.objects.all().order_by('-uploaded_at')
#     serializer_class = ExcelUploadSerializer


# class BudgetRecordListView(generics.ListAPIView):
#     serializer_class = BudgetRecordSerializer

#     def get_queryset(self):
#         qs = BudgetRecord.objects.all()
#         uid = self.request.query_params.get('upload_id')
#         if uid:
#             qs = qs.filter(upload_id=uid)
#         return qs


# # ─────────────────────────────────────────
# # RECAP VIEWS
# # ─────────────────────────────────────────

# # class RecapParRegionView(APIView):
# #     """
# #     GET /api/recap/region/?upload_id=1
# #     Retourne les totaux groupés par région avec le vrai nom.
# #     """
# #     def get(self, request):
# #         qs = BudgetRecord.objects.all()
# #         uid = request.query_params.get('upload_id')
# #         if uid:
# #             qs = qs.filter(upload_id=uid)

# #         # Exclure les régions nulles et les lignes de titre
# #         qs = qs.exclude(region__isnull=True).exclude(region__in=REGION_EXCLUSIONS)

# #         data = list(
# #             qs.values('region')
# #             .annotate(**build_aggregation())
# #             .order_by('region')
# #         )
# #         return Response(apply_mapping(data, 'region', REGION_MAPPING))
# class RecapParRegionView(APIView):

#     def get(self, request):
#         qs = BudgetRecord.objects.all()

#         uid = request.query_params.get('upload_id')
#         if uid:
#             qs = qs.filter(upload_id=uid)

#         qs = qs.exclude(region__isnull=True).exclude(region__in=REGION_EXCLUSIONS)

#         # 🔹 Détail par région
#         data = list(
#             qs.values('region')
#             .annotate(**build_aggregation())
#             .order_by('region')
#         )

#         data = apply_mapping(data, 'region', REGION_MAPPING)

#         # 🔹 TOTAL GLOBAL (division)
#         total = qs.aggregate(**build_aggregation())

#         return Response({
#             "regions": data,
#             "total_division": total
#         })

# # class RecapParFamilleView(APIView):
# #     """
# #     GET /api/recap/famille/?upload_id=1
# #     Retourne 7 lignes max (familles principales).
# #     2.1, 2.2, 2.61... → une seule ligne Maintenance Puits
# #     """
# #     def get(self, request):
# #         qs = BudgetRecord.objects.all()
# #         uid = request.query_params.get('upload_id')
# #         if uid:
# #             qs = qs.filter(upload_id=uid)

# #         # Exclure les familles nulles et titres
# #         qs = qs.exclude(famille__isnull=True).exclude(famille__in=FAMILLE_EXCLUSIONS)

# #         data = list(qs.values('famille').annotate(**build_aggregation()))
# #         return Response(group_by_famille(data))

# class RecapParFamilleView(APIView):
#     """
#     GET /api/recap/famille/?upload_id=1
#     Retourne 7 lignes max (familles principales)
#     + TOTAL DIVISION PRODUCTION
#     """

#     def get(self, request):
#         qs = BudgetRecord.objects.all()

#         uid = request.query_params.get('upload_id')
#         if uid:
#             qs = qs.filter(upload_id=uid)

#         # 🔹 Exclure familles invalides
#         qs = qs.exclude(famille__isnull=True).exclude(famille__in=FAMILLE_EXCLUSIONS)

#         # 🔹 Exclure region vide / 0 / null
#         qs = qs.exclude(region__isnull=True)\
#                .exclude(region__exact='')\
#                .exclude(region__exact='0')

#         # 🔹 Agrégation par famille
#         data = list(
#             qs.values('famille')
#             .annotate(**build_aggregation())
#         )

#         grouped = group_by_famille(data)

#         # 🔹 TOTAL DIVISION PRODUCTION
#         total_division = qs.aggregate(**build_aggregation())

#         return Response({
#             "familles": grouped,
#             "total_division_production": total_division
#         })
    
# class RecapParActiviteView(APIView):
#     """
#     GET /api/recap/activite/?upload_id=1
#     Retourne 2 lignes : Pétrole et Gaz.
#     """
#     def get(self, request):
#         qs = BudgetRecord.objects.all()
#         uid = request.query_params.get('upload_id')
#         if uid:
#             qs = qs.filter(upload_id=uid)

#         # Exclure les activités nulles et titres
#         qs = qs.exclude(activite__isnull=True).exclude(activite__in=ACTIVITE_EXCLUSIONS)

#         data = list(
#             qs.values('activite')
#             .annotate(**build_aggregation())
#             .order_by('activite')
#         )
#         return Response(apply_mapping(data, 'activite', ACTIVITE_MAPPING))


# class RecapGlobalView(APIView):
#     """
#     GET /api/recap/global/?upload_id=1
#     Retourne les 3 recaps en une seule requête.
#     """
#     def get(self, request):
#         qs = BudgetRecord.objects.all()
#         uid = request.query_params.get('upload_id')
#         if uid:
#             qs = qs.filter(upload_id=uid)

#         agg = build_aggregation()

#         # Région — exclure nulls et titres
#         region_qs = qs.exclude(region__isnull=True).exclude(region__in=REGION_EXCLUSIONS)
#         region_data = list(region_qs.values('region').annotate(**agg).order_by('region'))

#         # Famille — exclure nulls et titres
#         famille_qs = qs.exclude(famille__isnull=True).exclude(famille__in=FAMILLE_EXCLUSIONS)
#         famille_data = list(famille_qs.values('famille').annotate(**agg))

#         # Activité — exclure nulls et titres
#         activite_qs = qs.exclude(activite__isnull=True).exclude(activite__in=ACTIVITE_EXCLUSIONS)
#         activite_data = list(activite_qs.values('activite').annotate(**agg).order_by('activite'))

#         return Response({
#             'par_region':   apply_mapping(region_data, 'region', REGION_MAPPING),
#             'par_famille':  group_by_famille(famille_data),
#             'par_activite': apply_mapping(activite_data, 'activite', ACTIVITE_MAPPING),
#         })
    
# class RecapFamilleParActiviteView(APIView):
#     """
#     GET /api/recap/famille-par-activite/?upload_id=1
#     Retourne les familles groupées par activité + totaux
#     """
#     def get(self, request):
#         qs = BudgetRecord.objects.all()
#         uid = request.query_params.get('upload_id')
#         if uid:
#             qs = qs.filter(upload_id=uid)

#         # Exclure nulls et titres
#         qs = qs.exclude(activite__isnull=True).exclude(activite__in=ACTIVITE_EXCLUSIONS)
#         qs = qs.exclude(famille__isnull=True).exclude(famille__in=FAMILLE_EXCLUSIONS)

#         # Grouper par activite + famille
#         data = list(
#             qs.values('activite', 'famille')
#             .annotate(**build_aggregation())
#             .order_by('activite', 'famille')
#         )

#         # Restructurer : activite → familles groupées
#         activites = {}
#         for row in data:
#             act_code = str(row.get('activite', '') or '').strip()
#             act_nom  = ACTIVITE_MAPPING.get(act_code, act_code)
#             fam_nom  = get_famille_nom(str(row.get('famille', '') or '').strip())

#             if act_code not in activites:
#                 activites[act_code] = {
#                     'activite_code': act_code,
#                     'activite_nom':  act_nom,
#                     'familles': {},
#                     'total': {f: 0 for f in NUMERIC_FIELDS},
#                 }

#             # Ajouter ou accumuler la famille
#             if fam_nom not in activites[act_code]['familles']:
#                 activites[act_code]['familles'][fam_nom] = {
#                     'famille_nom': fam_nom,
#                     **{f: 0 for f in NUMERIC_FIELDS}
#                 }

#             for field in NUMERIC_FIELDS:
#                 val = float(row.get(field) or 0)
#                 activites[act_code]['familles'][fam_nom][field] += val
#                 activites[act_code]['total'][field] += val

#         # Formater le résultat final
#         result = []
#         total_global = {f: 0 for f in NUMERIC_FIELDS}

#         for act_code, act_data in sorted(activites.items()):
#             # Trier les familles dans l'ordre logique
#             familles_triees = sorted(
#                 act_data['familles'].values(),
#                 key=lambda x: FAMILLE_ORDER.index(x['famille_nom'])
#                 if x['famille_nom'] in FAMILLE_ORDER else 99
#             )

#             result.append({
#                 'activite_code': act_data['activite_code'],
#                 'activite_nom':  act_data['activite_nom'],
#                 'familles': familles_triees,
#                 'total_activite': act_data['total'],
#             })

#             # Accumuler le total global
#             for field in NUMERIC_FIELDS:
#                 total_global[field] += act_data['total'][field]

#         return Response({
#             'detail':        result,
#             'total_global':  total_global,
#         })
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from django.db.models import Sum
from .models import ExcelUpload, BudgetRecord
from .serializers import ExcelUploadSerializer, BudgetRecordSerializer, ExcelFileSerializer
from .utils import parse_excel
from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, FAMILLE_ORDER, get_famille_nom

# ─────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────

NUMERIC_FIELDS = [
    'cout_initial_total', 'cout_initial_dont_dex',
    'realisation_cumul_n_mins1_total', 'realisation_cumul_n_mins1_dont_dex',
    'real_s1_n_total', 'real_s1_n_dont_dex',
    'prev_s2_n_total', 'prev_s2_n_dont_dex',
    'prev_cloture_n_total', 'prev_cloture_n_dont_dex',
    'prev_n_plus1_total', 'prev_n_plus1_dont_dex',
    'reste_a_realiser_total', 'reste_a_realiser_dont_dex',
    'prev_n_plus2_total', 'prev_n_plus2_dont_dex',
    'prev_n_plus3_total', 'prev_n_plus3_dont_dex',
    'prev_n_plus4_total', 'prev_n_plus4_dont_dex',
    'prev_n_plus5_total', 'prev_n_plus5_dont_dex',
    'janvier_total', 'fevrier_total', 'mars_total',
    'avril_total', 'mai_total', 'juin_total',
    'juillet_total', 'aout_total', 'septembre_total',
    'octobre_total', 'novembre_total', 'decembre_total',
]

REGION_EXCLUSIONS   = [None, '', 'Région', 'REGION', 'region', 'Total', 'TOTAL']
FAMILLE_EXCLUSIONS  = [None, '', 'Famille', 'FAMILLE', 'famille', 'Total', 'TOTAL']
ACTIVITE_EXCLUSIONS = [None, '', 'Activité', 'ACTIVITE', 'activite', 'Total', 'TOTAL']


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def build_aggregation():
    return {f: Sum(f) for f in NUMERIC_FIELDS}


def apply_mapping(data, key_field, mapping):
    result = []
    for row in data:
        code = str(row.get(key_field, '') or '').strip()
        row[key_field + '_code'] = code
        row[key_field + '_nom'] = mapping.get(code, code)
        result.append(row)
    return result


def clean_queryset(qs):
    """
    🔥 Nettoyage GLOBAL des données
    """
    return qs.exclude(activite__isnull=True)\
             .exclude(activite__in=ACTIVITE_EXCLUSIONS)\
             .exclude(region__isnull=True)\
             .exclude(region__in=REGION_EXCLUSIONS)\
             .exclude(famille__isnull=True)\
             .exclude(famille__in=FAMILLE_EXCLUSIONS)


def group_by_famille(data):
    grouped = {}

    for row in data:
        code = str(row.get('famille', '') or '').strip()
        if not code:
            continue

        nom = get_famille_nom(code)

        if nom not in grouped:
            grouped[nom] = {field: 0 for field in NUMERIC_FIELDS}
            grouped[nom]['famille_nom'] = nom

        for field in NUMERIC_FIELDS:
            val = row.get(field) or 0
            grouped[nom][field] += float(val)

    return sorted(
        grouped.values(),
        key=lambda x: FAMILLE_ORDER.index(x['famille_nom'])
        if x['famille_nom'] in FAMILLE_ORDER else 99
    )


# ─────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────

class ExcelUploadView(APIView):
    def post(self, request):
        serializer = ExcelFileSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        file = serializer.validated_data['file']

        if not file.name.endswith(('.xlsx', '.xls')):
            return Response({'error': 'Only Excel files allowed'}, status=400)

        upload = ExcelUpload.objects.create(file_name=file.name, status='pending')

        try:
            count = parse_excel(file, upload)
            upload.status = 'processed'
            upload.save()

            return Response({
                'message': f'{count} records imported',
                'upload_id': upload.id
            }, status=201)

        except Exception as e:
            upload.status = 'failed'
            upload.save()
            return Response({'error': str(e)}, status=500)


class UploadListView(generics.ListAPIView):
    queryset = ExcelUpload.objects.all().order_by('-uploaded_at')
    serializer_class = ExcelUploadSerializer


class BudgetRecordListView(generics.ListAPIView):
    serializer_class = BudgetRecordSerializer

    def get_queryset(self):
        qs = BudgetRecord.objects.all()

        uid = self.request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        return clean_queryset(qs)


# ─────────────────────────────────────────
# RECAPS
# ─────────────────────────────────────────

class RecapParRegionView(APIView):

    def get(self, request):
        qs = BudgetRecord.objects.all()

        uid = request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        qs = clean_queryset(qs)

        data = list(
            qs.values('region')
            .annotate(**build_aggregation())
            .order_by('region')
        )

        total = qs.aggregate(**build_aggregation())

        return Response({
            "regions": apply_mapping(data, 'region', REGION_MAPPING),
            "total_division": total
        })


class RecapParFamilleView(APIView):

    def get(self, request):
        qs = BudgetRecord.objects.all()

        uid = request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        qs = clean_queryset(qs)

        data = list(
            qs.values('famille')
            .annotate(**build_aggregation())
        )

        return Response({
            "familles": group_by_famille(data),
            "total_division_production": qs.aggregate(**build_aggregation())
        })


# class RecapParActiviteView(APIView):

#     def get(self, request):
#         qs = BudgetRecord.objects.all()

#         uid = request.query_params.get('upload_id')
#         if uid:
#             qs = qs.filter(upload_id=uid)

#         qs = clean_queryset(qs)

#         data = list(
#             qs.values('activite')
#             .annotate(**build_aggregation())
#             .order_by('activite')
#         )

#         return Response(apply_mapping(data, 'activite', ACTIVITE_MAPPING))

class RecapParActiviteView(APIView):

    def get(self, request):
        qs = BudgetRecord.objects.all()

        uid = request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        qs = clean_queryset(qs)

        data = list(
            qs.values('activite')
            .annotate(**build_aggregation())
            .order_by('activite')
        )

        # Total Division — somme de toutes les activités
        total_qs = qs.aggregate(**build_aggregation())

        return Response({
            "activites": apply_mapping(data, 'activite', ACTIVITE_MAPPING),
            "total_division": total_qs,
        })
class RecapGlobalView(APIView):

    def get(self, request):
        qs = BudgetRecord.objects.all()

        uid = request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        qs = clean_queryset(qs)
        agg = build_aggregation()

        return Response({
            'par_region': apply_mapping(
                list(qs.values('region').annotate(**agg)),
                'region', REGION_MAPPING
            ),
            'par_famille': group_by_famille(
                list(qs.values('famille').annotate(**agg))
            ),
            'par_activite': apply_mapping(
                list(qs.values('activite').annotate(**agg)),
                'activite', ACTIVITE_MAPPING
            ),
        })


class RecapFamilleParActiviteView(APIView):

    def get(self, request):
        qs = BudgetRecord.objects.all()

        uid = request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        qs = clean_queryset(qs)

        data = list(
            qs.values('activite', 'famille')
            .annotate(**build_aggregation())
            .order_by('activite', 'famille')
        )

        activites = {}

        for row in data:
            act_code = str(row.get('activite') or '').strip()
            act_nom = ACTIVITE_MAPPING.get(act_code, act_code)
            fam_nom = get_famille_nom(str(row.get('famille') or '').strip())

            if act_code not in activites:
                activites[act_code] = {
                    'activite_code': act_code,
                    'activite_nom': act_nom,
                    'familles': {},
                    'total': {f: 0 for f in NUMERIC_FIELDS},
                }

            if fam_nom not in activites[act_code]['familles']:
                activites[act_code]['familles'][fam_nom] = {
                    'famille_nom': fam_nom,
                    **{f: 0 for f in NUMERIC_FIELDS}
                }

            for field in NUMERIC_FIELDS:
                val = float(row.get(field) or 0)
                activites[act_code]['familles'][fam_nom][field] += val
                activites[act_code]['total'][field] += val

        result = []
        total_global = {f: 0 for f in NUMERIC_FIELDS}

        for act in activites.values():
            familles = sorted(
                act['familles'].values(),
                key=lambda x: FAMILLE_ORDER.index(x['famille_nom'])
                if x['famille_nom'] in FAMILLE_ORDER else 99
            )

            result.append({
                'activite_code': act['activite_code'],
                'activite_nom': act['activite_nom'],
                'familles': familles,
                'total_activite': act['total'],
            })

            for f in NUMERIC_FIELDS:
                total_global[f] += act['total'][f]

        return Response({
            'detail': result,
            'total_global': total_global,
        })

# from rest_framework.views import APIView
# from django.http import HttpResponse
# from django.shortcuts import get_object_or_404
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.styles import getSampleStyleSheet
# from io import BytesIO

# from .models import BudgetRecord
# from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, get_famille_nom


# class BudgetRecordPDFView(APIView):

#     def get(self, request, pk):
#         # 🔹 Récupérer le record
#         record = get_object_or_404(BudgetRecord, pk=pk)

#         # 🔹 Mapping (code → nom réel)
#         activite_nom = ACTIVITE_MAPPING.get(record.activite, record.activite)
#         region_nom = REGION_MAPPING.get(record.region, record.region)
#         famille_nom = get_famille_nom(record.famille)

#         # 🔹 Création PDF
#         buffer = BytesIO()
#         doc = SimpleDocTemplate(buffer, pagesize=A4)

#         styles = getSampleStyleSheet()
#         elements = []

#         # ─────────────────────────────
#         # 🔹 TITRE
#         # ─────────────────────────────
#         elements.append(Paragraph(f"Budget Record #{record.id}", styles['Title']))
#         elements.append(Spacer(1, 12))

#         # ─────────────────────────────
#         # 🔹 INFOS GENERALES
#         # ─────────────────────────────
#         elements.append(Paragraph("<b>Informations générales</b>", styles['Heading2']))
#         elements.append(Spacer(1, 8))

#         elements.append(Paragraph(f"<b>Activité:</b> {activite_nom}", styles['Normal']))
#         elements.append(Paragraph(f"<b>Région:</b> {region_nom}", styles['Normal']))
#         elements.append(Paragraph(f"<b>Famille:</b> {famille_nom}", styles['Normal']))
#         elements.append(Paragraph(f"<b>Libellé:</b> {record.libelle or ''}", styles['Normal']))

#         elements.append(Spacer(1, 12))

#         # ─────────────────────────────
#         # 🔹 COUTS
#         # ─────────────────────────────
#         elements.append(Paragraph("<b>Coûts</b>", styles['Heading2']))
#         elements.append(Spacer(1, 8))

#         elements.append(Paragraph(f"Coût initial total: {record.cout_initial_total}", styles['Normal']))
#         elements.append(Paragraph(f"Coût initial DEX: {record.cout_initial_dont_dex}", styles['Normal']))

#         elements.append(Paragraph(f"Réalisation S1 total: {record.real_s1_n_total}", styles['Normal']))
#         elements.append(Paragraph(f"Réalisation S1 DEX: {record.real_s1_n_dont_dex}", styles['Normal']))

#         elements.append(Paragraph(f"Prévision S2 total: {record.prev_s2_n_total}", styles['Normal']))
#         elements.append(Paragraph(f"Prévision S2 DEX: {record.prev_s2_n_dont_dex}", styles['Normal']))

#         elements.append(Paragraph(f"Clôture total: {record.prev_cloture_n_total}", styles['Normal']))
#         elements.append(Paragraph(f"Clôture DEX: {record.prev_cloture_n_dont_dex}", styles['Normal']))

#         elements.append(Spacer(1, 12))

#         # ─────────────────────────────
#         # 🔹 RESTE + FUTUR
#         # ─────────────────────────────
#         elements.append(Paragraph("<b>Prévisions futures</b>", styles['Heading2']))
#         elements.append(Spacer(1, 8))

#         elements.append(Paragraph(f"Reste à réaliser: {record.reste_a_realiser_total}", styles['Normal']))
#         elements.append(Paragraph(f"N+1: {record.prev_n_plus1_total}", styles['Normal']))
#         elements.append(Paragraph(f"N+2: {record.prev_n_plus2_total}", styles['Normal']))
#         elements.append(Paragraph(f"N+3: {record.prev_n_plus3_total}", styles['Normal']))
#         elements.append(Paragraph(f"N+4: {record.prev_n_plus4_total}", styles['Normal']))
#         elements.append(Paragraph(f"N+5: {record.prev_n_plus5_total}", styles['Normal']))

#         elements.append(Spacer(1, 12))

#         # ─────────────────────────────
#         # 🔹 MENSUEL
#         # ─────────────────────────────
#         elements.append(Paragraph("<b>Répartition mensuelle</b>", styles['Heading2']))
#         elements.append(Spacer(1, 8))

#         elements.append(Paragraph(f"Janvier: {record.janvier_total}", styles['Normal']))
#         elements.append(Paragraph(f"Février: {record.fevrier_total}", styles['Normal']))
#         elements.append(Paragraph(f"Mars: {record.mars_total}", styles['Normal']))
#         elements.append(Paragraph(f"Avril: {record.avril_total}", styles['Normal']))
#         elements.append(Paragraph(f"Mai: {record.mai_total}", styles['Normal']))
#         elements.append(Paragraph(f"Juin: {record.juin_total}", styles['Normal']))
#         elements.append(Paragraph(f"Juillet: {record.juillet_total}", styles['Normal']))
#         elements.append(Paragraph(f"Août: {record.aout_total}", styles['Normal']))
#         elements.append(Paragraph(f"Septembre: {record.septembre_total}", styles['Normal']))
#         elements.append(Paragraph(f"Octobre: {record.octobre_total}", styles['Normal']))
#         elements.append(Paragraph(f"Novembre: {record.novembre_total}", styles['Normal']))
#         elements.append(Paragraph(f"Décembre: {record.decembre_total}", styles['Normal']))

#         # ─────────────────────────────
#         # 🔹 GENERATION PDF
#         # ─────────────────────────────
#         doc.build(elements)

#         buffer.seek(0)

#         return HttpResponse(
#             buffer,
#             content_type='application/pdf',
#             headers={
#                 'Content-Disposition': f'attachment; filename="budget_record_{record.id}.pdf"'
#             },
#         )
from rest_framework.views import APIView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

from .models import BudgetRecord
from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, get_famille_nom


class BudgetRecordPDFView(APIView):

    def get(self, request, pk):
        record = get_object_or_404(BudgetRecord, pk=pk)

        # 🔹 Mapping
        activite = ACTIVITE_MAPPING.get(record.activite, record.activite or '-')
        region = REGION_MAPPING.get(record.region, record.region or '-')
        famille = get_famille_nom(record.famille or '-')

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)

        styles = getSampleStyleSheet()
        elements = []

        # ─────────────────────────────
        # 🔷 HEADER
        # ─────────────────────────────
        elements.append(Paragraph("RAPPORT BUDGET", styles['Title']))
        elements.append(Spacer(1, 10))


        elements.append(Spacer(1, 10))

        # ─────────────────────────────
        # 🔷 INFOS GENERALES (TABLE)
        # ─────────────────────────────
        info_data = [
            ["Activité", activite],
            ["Région", region],
            ["Famille", famille],
            ["Libellé", record.libelle or '-'],
        ]

        info_table = Table(info_data, colWidths=[120, 350])

        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 15))

        # ─────────────────────────────
        # 🔷 TABLEAU COUTS
        # ─────────────────────────────
        couts_data = [
            ["Type", "Total", "Dont DEX"],
            ["Coût initial", record.cout_initial_total, record.cout_initial_dont_dex],
            ["Réalisation S1", record.real_s1_n_total, record.real_s1_n_dont_dex],
            ["Prévision S2", record.prev_s2_n_total, record.prev_s2_n_dont_dex],
            ["Clôture", record.prev_cloture_n_total, record.prev_cloture_n_dont_dex],
        ]

        couts_table = Table(couts_data)

        couts_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),

            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(Paragraph("<b>Coûts</b>", styles['Heading2']))
        elements.append(couts_table)
        elements.append(Spacer(1, 15))

        # ─────────────────────────────
        # 🔷 PREVISIONS
        # ─────────────────────────────
        prev_data = [
            ["Reste à réaliser", record.reste_a_realiser_total],
            ["N+1", record.prev_n_plus1_total],
            ["N+2", record.prev_n_plus2_total],
            ["N+3", record.prev_n_plus3_total],
            ["N+4", record.prev_n_plus4_total],
            ["N+5", record.prev_n_plus5_total],
        ]

        prev_table = Table(prev_data, colWidths=[200, 150])

        prev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(Paragraph("<b>Prévisions</b>", styles['Heading2']))
        elements.append(prev_table)
        elements.append(Spacer(1, 15))

        # ─────────────────────────────
        # 🔷 MENSUEL
        # ─────────────────────────────
        mensuel_data = [
            ["Mois", "Total"],
            ["Janvier", record.janvier_total],
            ["Février", record.fevrier_total],
            ["Mars", record.mars_total],
            ["Avril", record.avril_total],
            ["Mai", record.mai_total],
            ["Juin", record.juin_total],
            ["Juillet", record.juillet_total],
            ["Août", record.aout_total],
            ["Septembre", record.septembre_total],
            ["Octobre", record.octobre_total],
            ["Novembre", record.novembre_total],
            ["Décembre", record.decembre_total],
        ]

        mensuel_table = Table(mensuel_data)

        mensuel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(Paragraph("<b>Répartition mensuelle</b>", styles['Heading2']))
        elements.append(mensuel_table)

        # ─────────────────────────────
        # 🔷 BUILD PDF
        # ─────────────────────────────
        doc.build(elements)

        buffer.seek(0)

        return HttpResponse(
            buffer,
            content_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="budget_{record.id}.pdf"'
            },
        )