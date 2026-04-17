
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from django.db.models import Sum
from .models import ExcelUpload, BudgetRecord
from .serializers import ExcelUploadSerializer, BudgetRecordSerializer, ExcelFileSerializer
from .utils import auto_correct_records, parse_excel
from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, FAMILLE_ORDER, get_famille_nom
from .discovery import discover_service
from django.utils import timezone  # ✅ correct
# External service URLs
# SERVICE_1_URL = "http://localhost:8000"
# SERVICE_2_URL = "http://localhost:8001"
SERVICE1_APP = 'AUTHENTICATION-SERVICE'  # Nom utilisé dans Eureka
import requests
import xml.etree.ElementTree as ET

# ─────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────
def get_service1_url():
    try:
        res = requests.get("http://registry:8761/eureka/apps/AUTHENTICATION-SERVICE", headers={'Accept': 'application/json'})
        instances = res.json()['application']['instance']
        # If multiple instances, take the first one
        instance = instances[0] if isinstance(instances, list) else instances
        host = instance['hostName']
        port = instance['port']['$']
        return f"http://{host}:{port}"
    except Exception as e:
        print("Error resolving service1 from Eureka:", e)
        return "http://localhost:8001"  # Fallback
    
def get_service_param_url():
    """Découverte du SERVICE-NODE-PARAM via Eureka"""
    try:
        res = requests.get(
            "http://registry:8761/eureka/apps/SERVICE-NODE-PARAM",
            headers={'Accept': 'application/json'},
            timeout=5
        )
        instances = res.json()['application']['instance']
        instance = instances[0] if isinstance(instances, list) else instances
        host = instance['hostName']
        port = instance['port']['$']
        return f"http://{host}:{port}"
    except Exception as e:
        print("Error resolving SERVICE-NODE-PARAM from Eureka:", e)
        return "http://localhost:8083"  

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

PREVISION_FIELDS = [
    'prev_s2_n_total', 'prev_s2_n_dont_dex',
    'prev_cloture_n_total', 'prev_cloture_n_dont_dex',
    'prev_n_plus1_total', 'prev_n_plus1_dont_dex',
    'reste_a_realiser_total', 'reste_a_realiser_dont_dex',
    'prev_n_plus2_total', 'prev_n_plus2_dont_dex',
    'prev_n_plus3_total', 'prev_n_plus3_dont_dex',
    'prev_n_plus4_total', 'prev_n_plus4_dont_dex',
    'prev_n_plus5_total', 'prev_n_plus5_dont_dex',
]

SAISIE_FIELDS = [
    'cout_initial_total', 'cout_initial_dont_dex',
    'realisation_cumul_n_mins1_total', 'realisation_cumul_n_mins1_dont_dex',
    'real_s1_n_total', 'real_s1_n_dont_dex',
    'janvier_total', 'janvier_dont_dex',
    'fevrier_total', 'fevrier_dont_dex',
    'mars_total', 'mars_dont_dex',
    'avril_total', 'avril_dont_dex',
    'mai_total', 'mai_dont_dex',
    'juin_total', 'juin_dont_dex',
    'juillet_total', 'juillet_dont_dex',
    'aout_total', 'aout_dont_dex',
    'septembre_total', 'septembre_dont_dex',
    'octobre_total', 'octobre_dont_dex',
    'novembre_total', 'novembre_dont_dex',
    'decembre_total', 'decembre_dont_dex',
]

TOTAL_DONT_DEX_PAIRS = [
    ('cout_initial_total',              'cout_initial_dont_dex'),
    ('realisation_cumul_n_mins1_total', 'realisation_cumul_n_mins1_dont_dex'),
    ('real_s1_n_total',                 'real_s1_n_dont_dex'),
    ('janvier_total',                   'janvier_dont_dex'),
    ('fevrier_total',                   'fevrier_dont_dex'),
    ('mars_total',                      'mars_dont_dex'),
    ('avril_total',                     'avril_dont_dex'),
    ('mai_total',                       'mai_dont_dex'),
    ('juin_total',                      'juin_dont_dex'),
    ('juillet_total',                   'juillet_dont_dex'),
    ('aout_total',                      'aout_dont_dex'),
    ('septembre_total',                 'septembre_dont_dex'),
    ('octobre_total',                   'octobre_dont_dex'),
    ('novembre_total',                  'novembre_dont_dex'),
    ('decembre_total',                  'decembre_dont_dex'),
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
from rest_framework.permissions import IsAuthenticated
from .permissions import *
from .remote_auth import RemoteJWTAuthentication


#ancien upload
# class ExcelUploadView(APIView):
#     authentication_classes = [RemoteJWTAuthentication]
#     permission_classes = [IsAgent]

#     def post(self, request):
#         serializer = ExcelFileSerializer(data=request.data)

#         if not serializer.is_valid():
#             return Response(serializer.errors, status=400)

#         file = serializer.validated_data['file']

#         if not file.name.endswith(('.xlsx', '.xls')):
#             return Response({'error': 'Only Excel files allowed'}, status=400)

#         upload = ExcelUpload.objects.create(file_name=file.name, status='pending')

#         try:
#             count = parse_excel(file, upload)
#             upload.status = 'processed'
#             upload.save()

#             return Response({
#                 'message': f'{count} records imported',
#                 'upload_id': upload.id
#             }, status=201)

#         except Exception as e:
#             upload.status = 'failed'
#             upload.save()
#             return Response({'error': str(e)}, status=500)

#nouveau upload
class ExcelUploadView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]

    def post(self, request):
        serializer = ExcelFileSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        file = serializer.validated_data['file']

        if not file.name.endswith(('.xlsx', '.xls')):
            return Response({'error': 'Only Excel files allowed'}, status=400)

        upload = ExcelUpload.objects.create(file_name=file.name, status='pending')

        try:
            # 1. Import
            count = parse_excel(file, upload)

            # 2. Vérification + Correction automatique
            qs = clean_queryset(BudgetRecord.objects.filter(upload=upload))
            corrected_count = auto_correct_records(qs)

            upload.status = 'processed'
            upload.save()

            return Response({
                'message': f'{count} records importés',
                'upload_id': upload.id,
                'corrections': {
                    'records_corrigés': corrected_count,
                    'message': (
                        f'{corrected_count} record(s) corrigé(s) automatiquement'
                        if corrected_count
                        else 'Aucune correction nécessaire'
                    )
                }
            }, status=201)

        except Exception as e:
            upload.status = 'failed'
            upload.save()
            return Response({'error': str(e)}, status=500)

class UploadListView(generics.ListAPIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]
    
    queryset = ExcelUpload.objects.all().order_by('-uploaded_at')
    serializer_class = ExcelUploadSerializer


class BudgetRecordListView(generics.ListAPIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]
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
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]

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
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]

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



class RecapParActiviteView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]

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
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]

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
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]

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
class RecapRegionFamilleView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]
    """
    GET /api/recap/region-famille/?upload_id=1
    Retourne chaque région avec ses familles + total par région
    """

    def get(self, request):
        qs = BudgetRecord.objects.all()

        uid = request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        qs = clean_queryset(qs)

        # Grouper par région + famille
        data = list(
            qs.values('region', 'famille')
            .annotate(**build_aggregation())
            .order_by('region', 'famille')
        )

        # Restructurer : région → familles + total région
        regions = {}

        for row in data:
            reg_code = str(row.get('region') or '').strip()
            reg_nom  = REGION_MAPPING.get(reg_code, reg_code)
            fam_nom  = get_famille_nom(str(row.get('famille') or '').strip())

            if reg_code not in regions:
                regions[reg_code] = {
                    'region_code': reg_code,
                    'region_nom':  reg_nom,
                    'familles':    {},
                    'total':       {f: 0 for f in NUMERIC_FIELDS},
                }

            # Ajouter ou accumuler la famille
            if fam_nom not in regions[reg_code]['familles']:
                regions[reg_code]['familles'][fam_nom] = {
                    'famille_nom': fam_nom,
                    **{f: 0 for f in NUMERIC_FIELDS}
                }

            for field in NUMERIC_FIELDS:
                val = float(row.get(field) or 0)
                regions[reg_code]['familles'][fam_nom][field] += val
                regions[reg_code]['total'][field] += val

        # Formater le résultat
        result = []
        total_global = {f: 0 for f in NUMERIC_FIELDS}

        for reg_code, reg_data in sorted(regions.items()):
            # Trier les familles dans l'ordre logique
            familles_triees = sorted(
                reg_data['familles'].values(),
                key=lambda x: FAMILLE_ORDER.index(x['famille_nom'])
                if x['famille_nom'] in FAMILLE_ORDER else 99
            )

            result.append({
                'region_code':  reg_data['region_code'],
                'region_nom':   reg_data['region_nom'],
                'familles':     familles_triees,
                'total_region': reg_data['total'],
            })

            for f in NUMERIC_FIELDS:
                total_global[f] += reg_data['total'][f]

        return Response({
            'detail':       result,
            'total_global': total_global,
        })

from rest_framework.views import APIView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import datetime

from .models import BudgetRecord
from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, get_famille_nom


class BudgetRecordPDFView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        record = get_object_or_404(BudgetRecord, pk=pk)

        # 🔹 Année dynamique
        N = datetime.now().year  # N = année actuelle (ex: 2026)

        # 🔹 Mapping
        activite = ACTIVITE_MAPPING.get(record.activite, record.activite or '-')
        region   = REGION_MAPPING.get(record.region, record.region or '-')
        famille  = get_famille_nom(record.famille or '-')

        buffer = BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # ─────────────────────────────
        # 🔷 HEADER
        # ─────────────────────────────
        elements.append(Paragraph("RAPPORT BUDGET", styles['Title']))
        elements.append(Spacer(1, 10))

        # ─────────────────────────────
        # 🔷 INFOS GENERALES
        # ─────────────────────────────
        info_data = [
            ["Activité",  activite],
            ["Région",    region],
            ["Famille",   famille],
            ["Libellé",   record.libelle or '-'],
        ]

        info_table = Table(info_data, colWidths=[120, 350])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME',   (0, 0), (-1, -1), 'Helvetica'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))

        # ─────────────────────────────
        # 🔷 TABLEAU PRINCIPAL
        # ─────────────────────────────
        def v(val):
            """Affiche la valeur ou 0 si None."""
            return val if val is not None else 0

        main_data = [
            # En-tête
            ["Désignation", "Total", "Dont DEX"],

            # Coût Global Initial
            [
                f"Coût Global Initial PMT {N+1}/{N+5}",
                v(record.cout_initial_total),
                v(record.cout_initial_dont_dex),
            ],

            # Réalisations Cumulées N-1
            [
                f"Réalisations Cumulées à fin {N-1} au coût réel",
                v(record.realisation_cumul_n_mins1_total),
                v(record.realisation_cumul_n_mins1_dont_dex),
            ],

            # Prévisions de Clôture N
            [
                f"Prévisions de Clôture {N}",
                v(record.prev_cloture_n_total),
                v(record.prev_cloture_n_dont_dex),
            ],

            # Prévisions N+1
            [
                f"Prévisions {N+1}",
                v(record.prev_n_plus1_total),
                v(record.prev_n_plus1_dont_dex),
            ],

            # Reste à Réaliser N+2/N+5
            [
                f"Reste à Réaliser {N+2}/{N+5}",
                v(record.reste_a_realiser_total),
                v(record.reste_a_realiser_dont_dex),
            ],

            # Prévisions N+2
            [
                f"Prévisions {N+2}",
                v(record.prev_n_plus2_total),
                v(record.prev_n_plus2_dont_dex),
            ],

            # Prévisions N+3
            [
                f"Prévisions {N+3}",
                v(record.prev_n_plus3_total),
                v(record.prev_n_plus3_dont_dex),
            ],

            # Prévisions N+4
            [
                f"Prévisions {N+4}",
                v(record.prev_n_plus4_total),
                v(record.prev_n_plus4_dont_dex),
            ],

            # Prévisions N+5
            [
                f"Prévisions {N+5}",
                v(record.prev_n_plus5_total),
                v(record.prev_n_plus5_dont_dex),
            ],
        ]

        main_table = Table(main_data, colWidths=[280, 100, 100])
        main_table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),

            # Lignes alternées
            ('BACKGROUND', (0, 1), (-1, 1), colors.whitesmoke),
            ('BACKGROUND', (0, 3), (-1, 3), colors.whitesmoke),
            ('BACKGROUND', (0, 5), (-1, 5), colors.whitesmoke),
            ('BACKGROUND', (0, 7), (-1, 7), colors.whitesmoke),
            ('BACKGROUND', (0, 9), (-1, 9), colors.whitesmoke),

            ('ALIGN',  (1, 0), (-1, -1), 'CENTER'),
            ('GRID',   (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ]))

        elements.append(Paragraph("<b>Données budgétaires</b>", styles['Heading2']))
        elements.append(main_table)
        elements.append(Spacer(1, 15))

        # ─────────────────────────────
        # 🔷 MENSUEL — Prévisions N+2
        # ─────────────────────────────
        mensuel_data = [
            ["Mois", f"Prévisions {N+2} - Total", f"Prévisions {N+2} - Dont DEX"],
            ["Janvier",   v(record.janvier_total),   v(record.janvier_dont_dex)],
            ["Février",   v(record.fevrier_total),   v(record.fevrier_dont_dex)],
            ["Mars",      v(record.mars_total),      v(record.mars_dont_dex)],
            ["Avril",     v(record.avril_total),     v(record.avril_dont_dex)],
            ["Mai",       v(record.mai_total),       v(record.mai_dont_dex)],
            ["Juin",      v(record.juin_total),      v(record.juin_dont_dex)],
            ["Juillet",   v(record.juillet_total),   v(record.juillet_dont_dex)],
            ["Août",      v(record.aout_total),      v(record.aout_dont_dex)],
            ["Septembre", v(record.septembre_total), v(record.septembre_dont_dex)],
            ["Octobre",   v(record.octobre_total),   v(record.octobre_dont_dex)],
            ["Novembre",  v(record.novembre_total),  v(record.novembre_dont_dex)],
            ["Décembre",  v(record.decembre_total),  v(record.decembre_dont_dex)],
        ]

        mensuel_table = Table(mensuel_data, colWidths=[180, 150, 150])
        mensuel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN',  (1, 0), (-1, -1), 'CENTER'),
            ('GRID',   (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ]))

        elements.append(Paragraph(
            f"<b>Répartition mensuelle — Prévisions {N+2}</b>",
            styles['Heading2']
        ))
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
    
class VerificationCalculsView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]
    """
    GET /verification/?upload_id=1
    Vérifie la cohérence des calculs pour chaque record
    """

    def get(self, request):
        qs = BudgetRecord.objects.all()

        uid = request.query_params.get('upload_id')
        if uid:
            qs = qs.filter(upload_id=uid)

        qs = clean_queryset(qs)

        errors   = []
        warnings = []
        total    = qs.count()
        ok_count = 0

        TOLERANCE = 1  # tolérance d'arrondi

        def val(x):
            return float(x or 0)

        def check(record, label, gauche, droite):
            """Retourne une erreur si la différence dépasse la tolérance."""
            diff = abs(gauche - droite)
            if diff > TOLERANCE:
                return {
                    'record_id':  record.id,
                    'libelle':    record.libelle or '-',
                    'region':     REGION_MAPPING.get(record.region, record.region or '-'),
                    'famille':    get_famille_nom(record.famille or '-'),
                    'activite':   ACTIVITE_MAPPING.get(record.activite, record.activite or '-'),
                    'regle':      label,
                    'gauche':     round(gauche, 2),
                    'droite':     round(droite, 2),
                    'difference': round(diff, 2),
                }
            return None

        for record in qs:

            record_errors = []

            # ─────────────────────────────────────────
            # RÈGLE 1 : Réal. S1 + Prév. S2 = Prév. Clôture N
            # ─────────────────────────────────────────
            # Total
            e = check(
                record,
                "Réal.S1 (total) + Prév.S2 (total) = Prév.Clôture N (total)",
                val(record.real_s1_n_total) + val(record.prev_s2_n_total),
                val(record.prev_cloture_n_total),
            )
            if e: record_errors.append(e)

            # Dont DEX
            e = check(
                record,
                "Réal.S1 (DEX) + Prév.S2 (DEX) = Prév.Clôture N (DEX)",
                val(record.real_s1_n_dont_dex) + val(record.prev_s2_n_dont_dex),
                val(record.prev_cloture_n_dont_dex),
            )
            if e: record_errors.append(e)

            # ─────────────────────────────────────────
            # RÈGLE 2 : Reste à Réaliser = Prév N+2 + N+3 + N+4 + N+5
            # ─────────────────────────────────────────
            # Total
            e = check(
                record,
                "Reste à Réaliser (total) = Prév.N+2 + N+3 + N+4 + N+5 (total)",
                val(record.prev_n_plus2_total) + val(record.prev_n_plus3_total)
                + val(record.prev_n_plus4_total) + val(record.prev_n_plus5_total),
                val(record.reste_a_realiser_total),
            )
            if e: record_errors.append(e)

            # Dont DEX
            e = check(
                record,
                "Reste à Réaliser (DEX) = Prév.N+2 + N+3 + N+4 + N+5 (DEX)",
                val(record.prev_n_plus2_dont_dex) + val(record.prev_n_plus3_dont_dex)
                + val(record.prev_n_plus4_dont_dex) + val(record.prev_n_plus5_dont_dex),
                val(record.reste_a_realiser_dont_dex),
            )
            if e: record_errors.append(e)

            # ─────────────────────────────────────────
            # RÈGLE 3 : Prév. N+1 = Somme des mois (total)
            # ─────────────────────────────────────────
            somme_mois = (
                val(record.janvier_total)   + val(record.fevrier_total)  +
                val(record.mars_total)      + val(record.avril_total)    +
                val(record.mai_total)       + val(record.juin_total)     +
                val(record.juillet_total)   + val(record.aout_total)     +
                val(record.septembre_total) + val(record.octobre_total)  +
                val(record.novembre_total)  + val(record.decembre_total)
            )

            e = check(
                record,
                "Prév.N+1 (total) = Somme des 12 mois (total)",
                somme_mois,
                val(record.prev_n_plus1_total),
            )
            if e: record_errors.append(e)

            # ─────────────────────────────────────────
            # RÈGLE 4 : Coût Global = Réal.Cumul N-1 + Prév.Clôture N + Prév.N+1 + Reste à Réaliser
            # ─────────────────────────────────────────
            # Total
            e = check(
                record,
                "Coût Global (total) = Réal.Cumul N-1 + Prév.Clôture N + Prév.N+1 + Reste à Réaliser (total)",
                val(record.realisation_cumul_n_mins1_total) + val(record.prev_cloture_n_total)
                + val(record.prev_n_plus1_total) + val(record.reste_a_realiser_total),
                val(record.cout_initial_total),
            )
            if e: record_errors.append(e)

            # Dont DEX
            e = check(
                record,
                "Coût Global (DEX) = Réal.Cumul N-1 + Prév.Clôture N + Prév.N+1 + Reste à Réaliser (DEX)",
                val(record.realisation_cumul_n_mins1_dont_dex) + val(record.prev_cloture_n_dont_dex)
                + val(record.prev_n_plus1_dont_dex) + val(record.reste_a_realiser_dont_dex),
                val(record.cout_initial_dont_dex),
            )
            if e: record_errors.append(e)

            # ─────────────────────────────────────────
            if record_errors:
                errors.extend(record_errors)
            else:
                ok_count += 1

        return Response({
            'resume': {
                'total_records':  total,
                'records_ok':     ok_count,
                'records_errors': total - ok_count,
                'total_erreurs':  len(errors),
            },
            'erreurs': errors,
        })
    # ─────────────────────────────────────────
# SAISIE MANUELLE — NOUVEAU PROJET
# ─────────────────────────────────────────

class CreateBudgetRecordManuelView(APIView):
    """
    POST /api/budget/nouveau-projet/

    Création manuelle d'un BudgetRecord (nouveau projet)
    par le responsable structure uniquement.

    Règles :
    - region_id vient du TOKEN → nom_region résolu via SERVICE-NODE-PARAM
    - perimetre doit exister dans la region (filtré par region_id ObjectId)
    - famille doit exister dans ce perimetre de la region
    - total >= dont_dex pour chaque paire de champs
    - champs prévisions laissés vides (non saisissables)
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsResponsableStructure]

    def post(self, request):
        data = request.data
        errors = {}

        # ── 1. region_id + structure_id depuis le TOKEN ──
        region_id    = getattr(request.user, 'region_id', None)
        structure_id = getattr(request.user, 'structure_id', None)

        # Fallback body seulement si pas dans le token
        if not region_id:
            region_id = data.get('region_id')
        if not structure_id:
            structure_id = data.get('structure_id')

        if not region_id:
            return Response({'error': 'region_id introuvable dans le token'}, status=400)
        if not structure_id:
            return Response({'error': 'structure_id introuvable dans le token'}, status=400)

        # ── 2. Champs obligatoires ──
        activite       = data.get('activite')
        perimetre_code = data.get('perimetre')
        famille_code   = data.get('famille')
        code_division  = data.get('code_division')
        libelle        = data.get('libelle')

        if not activite:
            return Response({'error': 'activite est requis'}, status=400)
        if not perimetre_code:
            return Response({'error': 'perimetre est requis'}, status=400)
        if not famille_code:
            return Response({'error': 'famille est requis'}, status=400)
        if not code_division:
            return Response({'error': 'code_division est requis'}, status=400)
        if not libelle:
            return Response({'error': 'libelle est requis'}, status=400)

        service_url = get_service_param_url()
        token = request.headers.get('Authorization', '')

        # ── 3. Résolution région depuis region_id (ObjectId) ──
        try:
            region_resp = requests.get(
                f"{service_url}/params/regions/id/{region_id}",
                headers={'Authorization': token},
                timeout=5
            )

            print("=== DEBUG REGION ===")
            print("region_id      :", region_id)
            print("service_url    :", service_url)
            print("status_code    :", region_resp.status_code)
            print("body           :", region_resp.text)

            if region_resp.status_code != 200:
                return Response({'error': 'Région introuvable'}, status=400)

            region_data = region_resp.json().get('data', {})
            code_region = region_data.get('code_region')
            nom_region  = region_data.get('nom_region')

        except Exception as e:
            return Response({'error': f'Erreur service région: {str(e)}'}, status=503)

        # ── 4. Validation périmètre — filtré par region_id (ObjectId) ──
        try:
            perm_resp = requests.get(
                f"{service_url}/params/perimetres",
                params={'region': code_region},   # ✅ ObjectId, pas code_region
                headers={'Authorization': token},
                timeout=5
            )

            print("=== DEBUG PERIMETRE ===")
            print("params         :", {'region': region_id})
            print("status_code    :", perm_resp.status_code)
            print("body           :", perm_resp.text)

            perimetres_valides = [
                p['code_perimetre']
                for p in perm_resp.json().get('data', [])
            ]

            print("perimetres_valides:", perimetres_valides)
            print("perimetre_code    :", perimetre_code)

            if perimetre_code not in perimetres_valides:
                return Response({
                    'error': f"Le périmètre '{perimetre_code}' n'existe pas dans votre région",
                    'perimetres_disponibles': perimetres_valides
                }, status=400)

        except Exception as e:
            return Response({'error': f'Erreur service périmètre: {str(e)}'}, status=503)

        # ── 5. Validation famille — filtrée par region_id + perimetre_code ──
        try:
            fam_resp = requests.get(
                f"{service_url}/params/familles",
                params={'region': code_region, 'perimetre': perimetre_code},  # ✅ ObjectId
                headers={'Authorization': token},
                timeout=5
            )

            print("=== DEBUG FAMILLE ===")
            print("params         :", {'region': region_id, 'perimetre': perimetre_code})
            print("status_code    :", fam_resp.status_code)
            print("body           :", fam_resp.text)

            familles_valides = [
                f['code_famille']
                for f in fam_resp.json().get('data', [])
            ]

            print("familles_valides:", familles_valides)
            print("famille_code    :", famille_code)

            if famille_code not in familles_valides:
                return Response({
                    'error': f"La famille '{famille_code}' n'existe pas dans ce périmètre",
                    'familles_disponibles': familles_valides
                }, status=400)

        except Exception as e:
            return Response({'error': f'Erreur service famille: {str(e)}'}, status=503)

        # ── 6. Validation total >= dont_dex ──
        for total_field, dex_field in TOTAL_DONT_DEX_PAIRS:
            total_val = data.get(total_field)
            dex_val   = data.get(dex_field)
            if total_val is not None and dex_val is not None:
                if float(dex_val) > float(total_val):
                    errors[dex_field] = (
                        f"'{dex_field}' ({dex_val}) ne peut pas dépasser "
                        f"'{total_field}' ({total_val})"
                    )

        if errors:
            return Response({'errors': errors}, status=400)

        # ── 7. ExcelUpload factice pour traçabilité ──
        upload = ExcelUpload.objects.create(
            file_name=f"saisie_manuelle_structure_{structure_id}",
            status='processed'
        )

        # ── 8. Créer BudgetRecord ──
        record_data = {
            'upload':        upload,
            'activite':      activite,
            'region':        code_region,
            'perm':          perimetre_code,
            'famille':       famille_code,
            'code_division': code_division,
            'libelle':       libelle,
            'annee':         int(data.get('annee')) if data.get('annee') else None,  # ✅
        }

        # Champs saisie → None si non envoyés
        for field in SAISIE_FIELDS:
            val = data.get(field)
            record_data[field] = float(val) if val not in (None, '') else None

        # Champs prévisions → toujours None
        for field in PREVISION_FIELDS:
            record_data[field] = None

        record = BudgetRecord.objects.create(**record_data)

        return Response({
            'success': True,
            'message': 'Projet créé avec succès',
            'data': {
                'record_id':     record.id,
                'upload_id':     upload.id,
                'region_code':   code_region,
                'nom_region':    nom_region,
                'perimetre':     perimetre_code,
                'famille':       famille_code,
                'code_division': code_division,
                'libelle':       libelle,
            }
        }, status=201)
# ─────────────────────────────────────────
# GET + UPDATE BudgetRecord par code_division
# ─────────────────────────────────────────

# class BudgetRecordByCodeDivisionView(APIView):
#     """
#     GET  /api/budget/projet/<code_division>/  → récupérer le projet
#     PATCH /api/budget/projet/<code_division>/ → modifier + recalcul automatique
    
#     Règles :
#     - region ne peut pas être modifié
#     - Recalcul automatique des champs dérivés après modification
#     """
#     authentication_classes = [RemoteJWTAuthentication]
#     permission_classes = [IsResponsableStructure]

#     # ─────────────────────────────────────────
#     # GET
#     # ─────────────────────────────────────────
#     def get(self, request, code_division):
#         try:
#             record = BudgetRecord.objects.get(code_division=code_division)
#         except BudgetRecord.DoesNotExist:
#             return Response({'error': f"Projet '{code_division}' introuvable"}, status=404)
#         except BudgetRecord.MultipleObjectsReturned:
#             # Si plusieurs records avec le même code_division → retourner le plus récent
#             record = BudgetRecord.objects.filter(
#                 code_division=code_division
#             ).order_by('-id').first()

#         serializer = BudgetRecordSerializer(record)
#         return Response({
#             'success': True,
#             'data': serializer.data
#         })

#     # ─────────────────────────────────────────
#     # PATCH
#     # ─────────────────────────────────────────
#     def patch(self, request, code_division):
#         try:
#             record = BudgetRecord.objects.get(code_division=code_division)
#         except BudgetRecord.DoesNotExist:
#             return Response({'error': f"Projet '{code_division}' introuvable"}, status=404)
#         except BudgetRecord.MultipleObjectsReturned:
#             record = BudgetRecord.objects.filter(
#                 code_division=code_division
#             ).order_by('-id').first()

#         data = request.data

#         # ── 1. Région ne peut pas être modifiée ──
#         if 'region' in data:
#             return Response({
#                 'error': "La région ne peut pas être modifiée"
#             }, status=400)

#         # ── 2. Validation total >= dont_dex pour les champs envoyés ──
#         errors = {}
#         for total_field, dex_field in TOTAL_DONT_DEX_PAIRS:
#             # Récupérer la nouvelle valeur ou garder l'ancienne
#             total_val = float(data.get(total_field) or getattr(record, total_field) or 0)
#             dex_val   = float(data.get(dex_field)   or getattr(record, dex_field)   or 0)
#             if dex_val > total_val:
#                 errors[dex_field] = (
#                     f"'{dex_field}' ({dex_val}) ne peut pas dépasser "
#                     f"'{total_field}' ({total_val})"
#                 )

#         if errors:
#             return Response({'errors': errors}, status=400)

#         # ── 3. Appliquer les modifications (sauf region) ──
#         CHAMPS_MODIFIABLES = [
#             'activite', 'perm', 'famille', 'code_division',
#             'libelle', 'annee',
#         ] + SAISIE_FIELDS + PREVISION_FIELDS

#         for field in CHAMPS_MODIFIABLES:
#             if field in data:
#                 val = data[field]
#                 # Champs numériques
#                 if field in SAISIE_FIELDS or field in PREVISION_FIELDS:
#                     setattr(record, field, float(val) if val not in (None, '') else None)
#                 else:
#                     setattr(record, field, val)

#         # ── 4. Recalcul automatique des champs dérivés ──

#         def v(field):
#             """Retourner la valeur du record ou 0."""
#             val = getattr(record, field, None)
#             return float(val) if val is not None else 0.0

#         # RÈGLE 1 : Prév. Clôture N = Réal. S1 + Prév. S2
#         record.prev_cloture_n_total    = v('real_s1_n_total')    + v('prev_s2_n_total')
#         record.prev_cloture_n_dont_dex = v('real_s1_n_dont_dex') + v('prev_s2_n_dont_dex')

#         # RÈGLE 2 : Reste à Réaliser = Prév N+2 + N+3 + N+4 + N+5
#         record.reste_a_realiser_total = (
#             v('prev_n_plus2_total') + v('prev_n_plus3_total') +
#             v('prev_n_plus4_total') + v('prev_n_plus5_total')
#         )
#         record.reste_a_realiser_dont_dex = (
#             v('prev_n_plus2_dont_dex') + v('prev_n_plus3_dont_dex') +
#             v('prev_n_plus4_dont_dex') + v('prev_n_plus5_dont_dex')
#         )

#         # RÈGLE 3 : Prév. N+1 = Somme des 12 mois (total)
#         record.prev_n_plus1_total = (
#             v('janvier_total')   + v('fevrier_total')  + v('mars_total')  +
#             v('avril_total')     + v('mai_total')      + v('juin_total')  +
#             v('juillet_total')   + v('aout_total')     + v('septembre_total') +
#             v('octobre_total')   + v('novembre_total') + v('decembre_total')
#         )
#         record.prev_n_plus1_dont_dex = (
#             v('janvier_dont_dex')   + v('fevrier_dont_dex')  + v('mars_dont_dex')  +
#             v('avril_dont_dex')     + v('mai_dont_dex')      + v('juin_dont_dex')  +
#             v('juillet_dont_dex')   + v('aout_dont_dex')     + v('septembre_dont_dex') +
#             v('octobre_dont_dex')   + v('novembre_dont_dex') + v('decembre_dont_dex')
#         )

#         # RÈGLE 4 : Coût Global = Réal.Cumul N-1 + Prév.Clôture N + Prév.N+1 + Reste à Réaliser
#         record.cout_initial_total = (
#             v('realisation_cumul_n_mins1_total') +
#             v('prev_cloture_n_total') +
#             v('prev_n_plus1_total') +
#             v('reste_a_realiser_total')
#         )
#         record.cout_initial_dont_dex = (
#             v('realisation_cumul_n_mins1_dont_dex') +
#             v('prev_cloture_n_dont_dex') +
#             v('prev_n_plus1_dont_dex') +
#             v('reste_a_realiser_dont_dex')
#         )

#         # ── 5. Sauvegarder ──
#         record.save()

#         serializer = BudgetRecordSerializer(record)
#         return Response({
#             'success': True,
#             'message': 'Projet mis à jour avec recalcul automatique',
#             'recalculs': {
#                 'prev_cloture_n_total':       record.prev_cloture_n_total,
#                 'prev_cloture_n_dont_dex':    record.prev_cloture_n_dont_dex,
#                 'reste_a_realiser_total':     record.reste_a_realiser_total,
#                 'reste_a_realiser_dont_dex':  record.reste_a_realiser_dont_dex,
#                 'prev_n_plus1_total':         record.prev_n_plus1_total,
#                 'prev_n_plus1_dont_dex':      record.prev_n_plus1_dont_dex,
#                 'cout_initial_total':         record.cout_initial_total,
#                 'cout_initial_dont_dex':      record.cout_initial_dont_dex,
#             },
#             'data': serializer.data
#         })
class BudgetRecordByCodeDivisionView(APIView):
    """
    GET   /api/budget/projet/<code_division>/ → récupérer le projet
    PATCH /api/budget/projet/<code_division>/ → modifier + recalcul automatique

    Règles :
    - region ne peut pas être modifié
    - total >= dont_dex pour chaque paire (avant ET après recalcul)
    - Recalcul automatique des champs dérivés après modification
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsResponsableStructure]

    # ─────────────────────────────────────────
    # GET
    # ─────────────────────────────────────────
    def get(self, request, code_division):
        try:
            record = BudgetRecord.objects.get(code_division=code_division)
        except BudgetRecord.DoesNotExist:
            return Response({'error': f"Projet '{code_division}' introuvable"}, status=404)
        except BudgetRecord.MultipleObjectsReturned:
            record = BudgetRecord.objects.filter(
                code_division=code_division
            ).order_by('-id').first()

        serializer = BudgetRecordSerializer(record)
        return Response({
            'success': True,
            'data': serializer.data
        })

    # ─────────────────────────────────────────
    # PATCH
    # ─────────────────────────────────────────
    def patch(self, request, code_division):
        try:
            record = BudgetRecord.objects.get(code_division=code_division)
        except BudgetRecord.DoesNotExist:
            return Response({'error': f"Projet '{code_division}' introuvable"}, status=404)
        except BudgetRecord.MultipleObjectsReturned:
            record = BudgetRecord.objects.filter(
                code_division=code_division
            ).order_by('-id').first()

        data = request.data

        # ── 1. Région ne peut pas être modifiée ──
        if 'region' in data:
            return Response({
                'error': "La région ne peut pas être modifiée"
            }, status=400)

        # ── 2. Validation total >= dont_dex pour les champs envoyés ──
        errors = {}

        # Toutes les paires possibles (saisie + prévisions)
        ALL_TOTAL_DEX_PAIRS = TOTAL_DONT_DEX_PAIRS + [
            ('prev_s2_n_total',              'prev_s2_n_dont_dex'),
            ('prev_cloture_n_total',         'prev_cloture_n_dont_dex'),
            ('prev_n_plus1_total',           'prev_n_plus1_dont_dex'),
            ('reste_a_realiser_total',       'reste_a_realiser_dont_dex'),
            ('prev_n_plus2_total',           'prev_n_plus2_dont_dex'),
            ('prev_n_plus3_total',           'prev_n_plus3_dont_dex'),
            ('prev_n_plus4_total',           'prev_n_plus4_dont_dex'),
            ('prev_n_plus5_total',           'prev_n_plus5_dont_dex'),
            ('cout_initial_total',           'cout_initial_dont_dex'),
            ('realisation_cumul_n_mins1_total', 'realisation_cumul_n_mins1_dont_dex'),
        ]

        for total_field, dex_field in ALL_TOTAL_DEX_PAIRS:
            # Nouvelle valeur si envoyée, sinon ancienne valeur du record
            total_val = float(data.get(total_field) if data.get(total_field) is not None
                              else getattr(record, total_field) or 0)
            dex_val   = float(data.get(dex_field)   if data.get(dex_field)   is not None
                              else getattr(record, dex_field)   or 0)
            if dex_val > total_val:
                errors[dex_field] = (
                    f"'{dex_field}' ({dex_val}) ne peut pas dépasser "
                    f"'{total_field}' ({total_val})"
                )

        if errors:
            return Response({'errors': errors}, status=400)

        # ── 3. Appliquer les modifications (sauf region) ──
        CHAMPS_MODIFIABLES = [
            'activite', 'perm', 'famille', 'code_division',
            'libelle', 'annee',
        ] + SAISIE_FIELDS + PREVISION_FIELDS

        for field in CHAMPS_MODIFIABLES:
            if field in data:
                val = data[field]
                if field in SAISIE_FIELDS or field in PREVISION_FIELDS:
                    setattr(record, field, float(val) if val not in (None, '') else None)
                else:
                    setattr(record, field, val)

        # ── 4. Recalcul automatique des champs dérivés ──
        def v(field):
            val = getattr(record, field, None)
            return float(val) if val is not None else 0.0

        # RÈGLE 1 : Prév. Clôture N = Réal. S1 + Prév. S2
        record.prev_cloture_n_total    = v('real_s1_n_total')    + v('prev_s2_n_total')
        record.prev_cloture_n_dont_dex = v('real_s1_n_dont_dex') + v('prev_s2_n_dont_dex')

        # RÈGLE 2 : Reste à Réaliser = Prév N+2 + N+3 + N+4 + N+5
        record.reste_a_realiser_total = (
            v('prev_n_plus2_total') + v('prev_n_plus3_total') +
            v('prev_n_plus4_total') + v('prev_n_plus5_total')
        )
        record.reste_a_realiser_dont_dex = (
            v('prev_n_plus2_dont_dex') + v('prev_n_plus3_dont_dex') +
            v('prev_n_plus4_dont_dex') + v('prev_n_plus5_dont_dex')
        )

        # RÈGLE 3 : Prév. N+1 = Somme des 12 mois
        record.prev_n_plus1_total = (
            v('janvier_total')    + v('fevrier_total')    + v('mars_total')      +
            v('avril_total')      + v('mai_total')        + v('juin_total')      +
            v('juillet_total')    + v('aout_total')       + v('septembre_total') +
            v('octobre_total')    + v('novembre_total')   + v('decembre_total')
        )
        record.prev_n_plus1_dont_dex = (
            v('janvier_dont_dex')    + v('fevrier_dont_dex')    + v('mars_dont_dex')      +
            v('avril_dont_dex')      + v('mai_dont_dex')        + v('juin_dont_dex')      +
            v('juillet_dont_dex')    + v('aout_dont_dex')       + v('septembre_dont_dex') +
            v('octobre_dont_dex')    + v('novembre_dont_dex')   + v('decembre_dont_dex')
        )

        # RÈGLE 4 : Coût Global = Réal.Cumul N-1 + Prév.Clôture N + Prév.N+1 + Reste à Réaliser
        record.cout_initial_total = (
            v('realisation_cumul_n_mins1_total') +
            v('prev_cloture_n_total')            +
            v('prev_n_plus1_total')              +
            v('reste_a_realiser_total')
        )
        record.cout_initial_dont_dex = (
            v('realisation_cumul_n_mins1_dont_dex') +
            v('prev_cloture_n_dont_dex')            +
            v('prev_n_plus1_dont_dex')              +
            v('reste_a_realiser_dont_dex')
        )

        # ── 5. Vérification finale après recalcul — dont_dex <= total ──
        recalcul_errors = {}

        RECALCUL_PAIRS = [
            ('prev_cloture_n_total',         'prev_cloture_n_dont_dex'),
            ('reste_a_realiser_total',       'reste_a_realiser_dont_dex'),
            ('prev_n_plus1_total',           'prev_n_plus1_dont_dex'),
            ('cout_initial_total',           'cout_initial_dont_dex'),
        ]

        for total_field, dex_field in RECALCUL_PAIRS:
            total_val = v(total_field)
            dex_val   = v(dex_field)
            if dex_val > total_val:
                recalcul_errors[dex_field] = (
                    f"Après recalcul : '{dex_field}' ({dex_val}) "
                    f"dépasse '{total_field}' ({total_val})"
                )

        if recalcul_errors:
            return Response({
                'error': 'Incohérence après recalcul — vérifiez vos données',
                'errors': recalcul_errors
            }, status=400)

        # ── 6. Sauvegarder ──
        record.save()

        serializer = BudgetRecordSerializer(record)
        return Response({
            'success': True,
            'message': 'Projet mis à jour avec recalcul automatique',
            'recalculs': {
                'prev_cloture_n_total':      record.prev_cloture_n_total,
                'prev_cloture_n_dont_dex':   record.prev_cloture_n_dont_dex,
                'reste_a_realiser_total':    record.reste_a_realiser_total,
                'reste_a_realiser_dont_dex': record.reste_a_realiser_dont_dex,
                'prev_n_plus1_total':        record.prev_n_plus1_total,
                'prev_n_plus1_dont_dex':     record.prev_n_plus1_dont_dex,
                'cout_initial_total':        record.cout_initial_total,
                'cout_initial_dont_dex':     record.cout_initial_dont_dex,
            },
            'data': serializer.data
        })
    from django.utils import timezone

# ─────────────────────────────────────────
# HELPER — récupérer record par id
# ─────────────────────────────────────────
def get_record_or_404(record_id):
    try:
        return BudgetRecord.objects.get(id=record_id)
    except BudgetRecord.DoesNotExist:
        return None


# ─────────────────────────────────────────
# ÉTAPE 0 — Soumettre (responsable structure)
# ─────────────────────────────────────────
class SoumettreProjetView(APIView):
    """
    POST /recap/budget/soumettre/<id>/
    Responsable structure soumet le projet pour validation
    Condition : statut = brouillon
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsResponsableStructure]

    def post(self, request, record_id):
        record = get_record_or_404(record_id)
        if not record:
            return Response({'error': 'Projet introuvable'}, status=404)

        if record.statut != 'brouillon':
            return Response({
                'error': f"Impossible de soumettre — statut actuel : '{record.statut}'"
            }, status=400)

        record.statut = 'soumis'
        record.save()

        return Response({
            'success': True,
            'message': 'Projet soumis pour validation',
            'statut': record.statut
        })


# ─────────────────────────────────────────
# ÉTAPE 1 — Validation Directeur Région
# ─────────────────────────────────────────
class ValiderDirecteurRegionView(APIView):
    """
    POST /recap/budget/valider/directeur-region/<id>/
    Condition : statut = soumis
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsDirecteurRegion]

    def post(self, request, record_id):
        record = get_record_or_404(record_id)
        if not record:
            return Response({'error': 'Projet introuvable'}, status=404)

        action      = request.data.get('action')       # 'valider' ou 'rejeter'
        commentaire = request.data.get('commentaire', '')

        if action not in ['valider', 'rejeter']:
            return Response({'error': "action doit être 'valider' ou 'rejeter'"}, status=400)

        # ── Condition : doit être soumis ──
        if record.statut != 'soumis':
            return Response({
                'error': f"Le projet doit être 'soumis' — statut actuel : '{record.statut}'"
            }, status=400)

        if action == 'valider':
            record.statut                            = 'valide_directeur_region'
            record.valide_par_directeur_region       = request.user.nom_complet
            record.date_validation_directeur_region  = timezone.now()
            record.commentaire_directeur_region      = commentaire
            message = 'Projet validé par le directeur région'
        else:
            record.statut       = 'rejete'
            record.rejete_par   = request.user.nom_complet
            record.date_rejet   = timezone.now()
            record.motif_rejet  = commentaire
            message = 'Projet rejeté par le directeur région'

        record.save()

        return Response({
            'success': True,
            'message': message,
            'statut':  record.statut
        })


# ─────────────────────────────────────────
# ÉTAPE 2 — Validation Chef
# ─────────────────────────────────────────
class ValiderChefView(APIView):
    """
    POST /recap/budget/valider/chef/<id>/
    Condition : statut = valide_directeur_region
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsChef]

    def post(self, request, record_id):
        record = get_record_or_404(record_id)
        if not record:
            return Response({'error': 'Projet introuvable'}, status=404)

        action      = request.data.get('action')
        commentaire = request.data.get('commentaire', '')

        if action not in ['valider', 'rejeter']:
            return Response({'error': "action doit être 'valider' ou 'rejeter'"}, status=400)

        # ── Condition : doit être validé par directeur région ──
        if record.statut != 'valide_directeur_region':
            return Response({
                'error': f"Le projet doit être 'valide_directeur_region' — statut actuel : '{record.statut}'"
            }, status=400)

        if action == 'valider':
            record.statut               = 'valide_chef'
            record.valide_par_chef      = request.user.nom_complet
            record.date_validation_chef = timezone.now()
            record.commentaire_chef     = commentaire
            message = 'Projet validé par le chef'
        else:
            record.statut      = 'rejete'
            record.rejete_par  = request.user.nom_complet
            record.date_rejet  = timezone.now()
            record.motif_rejet = commentaire
            message = 'Projet rejeté par le chef'

        record.save()

        return Response({
            'success': True,
            'message': message,
            'statut':  record.statut
        })


# ─────────────────────────────────────────
# ÉTAPE 3 — Validation Directeur
# ─────────────────────────────────────────
class ValiderDirecteurView(APIView):
    """
    POST /recap/budget/valider/directeur/<id>/
    Condition : statut = valide_chef
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsDirecteur]

    def post(self, request, record_id):
        record = get_record_or_404(record_id)
        if not record:
            return Response({'error': 'Projet introuvable'}, status=404)

        action      = request.data.get('action')
        commentaire = request.data.get('commentaire', '')

        if action not in ['valider', 'rejeter']:
            return Response({'error': "action doit être 'valider' ou 'rejeter'"}, status=400)

        # ── Condition : doit être validé par chef ──
        if record.statut != 'valide_chef':
            return Response({
                'error': f"Le projet doit être 'valide_chef' — statut actuel : '{record.statut}'"
            }, status=400)

        if action == 'valider':
            record.statut                    = 'valide_directeur'
            record.valide_par_directeur      = request.user.nom_complet
            record.date_validation_directeur = timezone.now()
            record.commentaire_directeur     = commentaire
            message = 'Projet validé par le directeur'
        else:
            record.statut      = 'rejete'
            record.rejete_par  = request.user.nom_complet
            record.date_rejet  = timezone.now()
            record.motif_rejet = commentaire
            message = 'Projet rejeté par le directeur'

        record.save()

        return Response({
            'success': True,
            'message': message,
            'statut':  record.statut
        })


# ─────────────────────────────────────────
# ÉTAPE 4 — Validation Divisionnaire
# ─────────────────────────────────────────
class ValiderDivisionnnaireView(APIView):
    """
    POST /recap/budget/valider/divisionnaire/<id>/
    Condition : statut = valide_directeur
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsDivisionnaire]  # ton permission existant

    def post(self, request, record_id):
        record = get_record_or_404(record_id)
        if not record:
            return Response({'error': 'Projet introuvable'}, status=404)

        action      = request.data.get('action')
        commentaire = request.data.get('commentaire', '')

        if action not in ['valider', 'rejeter']:
            return Response({'error': "action doit être 'valider' ou 'rejeter'"}, status=400)

        # ── Condition : doit être validé par directeur ──
        if record.statut != 'valide_directeur':
            return Response({
                'error': f"Le projet doit être 'valide_directeur' — statut actuel : '{record.statut}'"
            }, status=400)

        if action == 'valider':
            record.statut                        = 'valide_divisionnaire'
            record.valide_par_divisionnaire      = request.user.nom_complet
            record.date_validation_divisionnaire = timezone.now()
            record.commentaire_divisionnaire     = commentaire
            message = 'Projet validé par le divisionnaire — validation complète ✅'
        else:
            record.statut      = 'rejete'
            record.rejete_par  = request.user.nom_complet
            record.date_rejet  = timezone.now()
            record.motif_rejet = commentaire
            message = 'Projet rejeté par le divisionnaire'

        record.save()

        return Response({
            'success': True,
            'message': message,
            'statut':  record.statut
        })
    # ─────────────────────────────────────────
# GET — Statut complet du workflow de validation
# ─────────────────────────────────────────
class StatutValidationView(APIView):
    """
    GET /recap/budget/statut/<record_id>/
    Retourne le statut complet du workflow de validation
    Accessible par tous les rôles
    """
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAgent]

    def get(self, request, record_id):
        record = get_record_or_404(record_id)
        if not record:
            return Response({'error': 'Projet introuvable'}, status=404)

        # ── Progression du workflow ──
        WORKFLOW = [
            'brouillon',
            'soumis',
            'valide_directeur_region',
            'valide_chef',
            'valide_directeur',
            'valide_divisionnaire',
        ]

        statut_actuel = record.statut
        est_rejete    = statut_actuel == 'rejete'

        # Calculer la progression
        if est_rejete:
            progression = 0
        else:
            try:
                etape_actuelle = WORKFLOW.index(statut_actuel)
                progression    = round((etape_actuelle / (len(WORKFLOW) - 1)) * 100)
            except ValueError:
                progression = 0

        # ── Étapes détaillées ──
        etapes = [
            {
                'etape':       0,
                'label':       'Création',
                'role':        'responsable_structure',
                'statut_cible': 'brouillon',
                'fait':        True,
                'date':        None,
                'par':         None,
                'commentaire': None,
            },
            {
                'etape':        1,
                'label':        'Soumission',
                'role':         'responsable_structure',
                'statut_cible': 'soumis',
                'fait':         statut_actuel in (
                                    'soumis',
                                    'valide_directeur_region',
                                    'valide_chef',
                                    'valide_directeur',
                                    'valide_divisionnaire'
                                ),
                'date':         None,
                'par':          None,
                'commentaire':  None,
            },
            {
                'etape':        2,
                'label':        'Validation Directeur Région',
                'role':         'directeur_region',
                'statut_cible': 'valide_directeur_region',
                'fait':         statut_actuel in (
                                    'valide_directeur_region',
                                    'valide_chef',
                                    'valide_directeur',
                                    'valide_divisionnaire'
                                ),
                'date':         record.date_validation_directeur_region,
                'par':          record.valide_par_directeur_region,
                'commentaire':  record.commentaire_directeur_region,
            },
            {
                'etape':        3,
                'label':        'Validation Chef',
                'role':         'chef',
                'statut_cible': 'valide_chef',
                'fait':         statut_actuel in (
                                    'valide_chef',
                                    'valide_directeur',
                                    'valide_divisionnaire'
                                ),
                'date':         record.date_validation_chef,
                'par':          record.valide_par_chef,
                'commentaire':  record.commentaire_chef,
            },
            {
                'etape':        4,
                'label':        'Validation Directeur',
                'role':         'directeur',
                'statut_cible': 'valide_directeur',
                'fait':         statut_actuel in (
                                    'valide_directeur',
                                    'valide_divisionnaire'
                                ),
                'date':         record.date_validation_directeur,
                'par':          record.valide_par_directeur,
                'commentaire':  record.commentaire_directeur,
            },
            {
                'etape':        5,
                'label':        'Validation Divisionnaire',
                'role':         'divisionnaire',
                'statut_cible': 'valide_divisionnaire',
                'fait':         statut_actuel == 'valide_divisionnaire',
                'date':         record.date_validation_divisionnaire,
                'par':          record.valide_par_divisionnaire,
                'commentaire':  record.commentaire_divisionnaire,
            },
        ]

        # ── Prochaine étape ──
        prochaine_etape = None
        if not est_rejete and statut_actuel != 'valide_divisionnaire':
            mapping_prochaine = {
                'brouillon':               {'action': 'Soumettre',                  'role': 'responsable_structure', 'url': f'/recap/budget/soumettre/{record_id}/'},
                'soumis':                  {'action': 'Valider (Directeur Région)', 'role': 'directeur_region',      'url': f'/recap/budget/valider/directeur-region/{record_id}/'},
                'valide_directeur_region': {'action': 'Valider (Chef)',             'role': 'chef',                  'url': f'/recap/budget/valider/chef/{record_id}/'},
                'valide_chef':             {'action': 'Valider (Directeur)',        'role': 'directeur',             'url': f'/recap/budget/valider/directeur/{record_id}/'},
                'valide_directeur':        {'action': 'Valider (Divisionnaire)',    'role': 'divisionnaire',         'url': f'/recap/budget/valider/divisionnaire/{record_id}/'},
            }
            prochaine_etape = mapping_prochaine.get(statut_actuel)

        return Response({
            'success': True,
            'projet': {
                'id':            record.id,
                'code_division': record.code_division,
                'libelle':       record.libelle,
                'region':        record.region,
                'annee':         record.annee,
            },
            'validation': {
                'statut_actuel':   statut_actuel,
                'est_valide':      statut_actuel == 'valide_divisionnaire',
                'est_rejete':      est_rejete,
                'progression':     f"{progression}%",
                'prochaine_etape': prochaine_etape,

                # Rejet info
                'rejet': {
                    'rejete_par':  record.rejete_par,
                    'date_rejet':  record.date_rejet,
                    'motif':       record.motif_rejet,
                } if est_rejete else None,

                # Workflow complet
                'etapes': etapes,
            }
        })

