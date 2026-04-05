
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from django.db.models import Sum
from .models import ExcelUpload, BudgetRecord
from .serializers import ExcelUploadSerializer, BudgetRecordSerializer, ExcelFileSerializer
from .utils import auto_correct_records, parse_excel
from .mappings import REGION_MAPPING, ACTIVITE_MAPPING, FAMILLE_ORDER, get_famille_nom

from .discovery import discover_service

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
        return "http://localhost:8000"  # Fallback

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
from rest_framework.permissions import IsAuthenticated
from .permissions import IsDirecteur, IsVisionnaire, IsChef, IsAgent
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
    permission_classes = [IsAgent]

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