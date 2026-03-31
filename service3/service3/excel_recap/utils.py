# import pandas as pd
# from decimal import Decimal, InvalidOperation

# def safe_decimal(value):
#     try:
#         if pd.isna(value):
#             return None
#         return Decimal(str(value))
#     except (InvalidOperation, TypeError):
#         return None

# def parse_excel(file, upload_instance):
#     from .models import BudgetRecord

#     df = pd.read_excel(file, skiprows=2, header=None)

#     records = []
#     for _, row in df.iterrows():
#         if len(row) < 6:
#             continue
#         record = BudgetRecord(
#             upload=upload_instance,
#             activite=str(row.iloc[0]) if pd.notna(row.iloc[0]) else None,
#             region=str(row.iloc[1]) if pd.notna(row.iloc[1]) else None,
#             perm=str(row.iloc[2]) if pd.notna(row.iloc[2]) else None,
#             famille=str(row.iloc[3]) if pd.notna(row.iloc[3]) else None,
#             code_division=str(row.iloc[4]) if pd.notna(row.iloc[4]) else None,
#             libelle=str(row.iloc[5]) if pd.notna(row.iloc[5]) else None,
#             credit_initial_total=safe_decimal(row.iloc[6]) if len(row) > 6 else None,
#             credit_initial_dont_dex=safe_decimal(row.iloc[7]) if len(row) > 7 else None,
#             realisation_cumul_total=safe_decimal(row.iloc[8]) if len(row) > 8 else None,
#             realisation_cumul_dont_dex=safe_decimal(row.iloc[9]) if len(row) > 9 else None,
#             real_s1_total=safe_decimal(row.iloc[10]) if len(row) > 10 else None,
#             real_s1_dont_dex=safe_decimal(row.iloc[11]) if len(row) > 11 else None,
#             prev_s2_total=safe_decimal(row.iloc[12]) if len(row) > 12 else None,
#             prev_s2_dont_dex=safe_decimal(row.iloc[13]) if len(row) > 13 else None,
#             prev_cloture_total=safe_decimal(row.iloc[14]) if len(row) > 14 else None,
#             prev_2016_total=safe_decimal(row.iloc[16]) if len(row) > 16 else None,
#             reste_a_realiser_total=safe_decimal(row.iloc[18]) if len(row) > 18 else None,
#             prev_2017_total=safe_decimal(row.iloc[20]) if len(row) > 20 else None,
#             prev_2018_total=safe_decimal(row.iloc[22]) if len(row) > 22 else None,
#             prev_2019_total=safe_decimal(row.iloc[24]) if len(row) > 24 else None,
#             janvier_total=safe_decimal(row.iloc[26]) if len(row) > 26 else None,
#             fevrier_total=safe_decimal(row.iloc[28]) if len(row) > 28 else None,
#             mars_total=safe_decimal(row.iloc[30]) if len(row) > 30 else None,
#             avril_total=safe_decimal(row.iloc[32]) if len(row) > 32 else None,
#             mai_total=safe_decimal(row.iloc[34]) if len(row) > 34 else None,
#             juin_total=safe_decimal(row.iloc[36]) if len(row) > 36 else None,
#             juillet_total=safe_decimal(row.iloc[38]) if len(row) > 38 else None,
#             aout_total=safe_decimal(row.iloc[40]) if len(row) > 40 else None,
#             septembre_total=safe_decimal(row.iloc[42]) if len(row) > 42 else None,
#             octobre_total=safe_decimal(row.iloc[44]) if len(row) > 44 else None,
#             novembre_total=safe_decimal(row.iloc[46]) if len(row) > 46 else None,
#             decembre_total=safe_decimal(row.iloc[48]) if len(row) > 48 else None,
#         )
#         records.append(record)

#     BudgetRecord.objects.bulk_create(records)
#     return len(records)
import pandas as pd
from decimal import Decimal, InvalidOperation

def safe_decimal(value):
    try:
        if pd.isna(value):
            return None
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None

def parse_excel(file, upload_instance):
    from .models import BudgetRecord

    if file.name.endswith('.xls'):
        engine = 'xlrd'
    else:
        engine = 'openpyxl'

    df = pd.read_excel(file, skiprows=2, header=None, engine=engine)

    records = []
    for _, row in df.iterrows():
        if len(row) < 6:
            continue

        def get(i):
            return safe_decimal(row.iloc[i]) if len(row) > i else None

        record = BudgetRecord(
            upload=upload_instance,
            activite=str(row.iloc[0]) if pd.notna(row.iloc[0]) else None,
            region=str(row.iloc[1])   if pd.notna(row.iloc[1]) else None,
            perm=str(row.iloc[2])     if pd.notna(row.iloc[2]) else None,
            famille=str(row.iloc[3])  if pd.notna(row.iloc[3]) else None,
            code_division=str(row.iloc[4]) if pd.notna(row.iloc[4]) else None,
            libelle=str(row.iloc[5])  if pd.notna(row.iloc[5]) else None,

            # Coût initial
            cout_initial_total=get(6),
            cout_initial_dont_dex=get(7),

            # Réalisation cumulée N-1
            realisation_cumul_n_mins1_total=get(8),
            realisation_cumul_n_mins1_dont_dex=get(9),

            # Réalisation S1 N
            real_s1_n_total=get(10),
            real_s1_n_dont_dex=get(11),

            # Prévision S2 N
            prev_s2_n_total=get(12),
            prev_s2_n_dont_dex=get(13),

            # Prévision clôture N
            prev_cloture_n_total=get(14),
            prev_cloture_n_dont_dex=get(15),

            # Prévision N+1
            prev_n_plus1_total=get(16),
            prev_n_plus1_dont_dex=get(17),

            # Reste à réaliser
            reste_a_realiser_total=get(18),
            reste_a_realiser_dont_dex=get(19),

            # Prévision N+2
            prev_n_plus2_total=get(20),
            prev_n_plus2_dont_dex=get(21),

            # Prévision N+3
            prev_n_plus3_total=get(22),
            prev_n_plus3_dont_dex=get(23),

            # Prévision N+4
            prev_n_plus4_total=get(24),
            prev_n_plus4_dont_dex=get(25),

            # Prévision N+5
            prev_n_plus5_total=get(26),
            prev_n_plus5_dont_dex=get(27),

            # Mensuel
            janvier_total=get(28),    janvier_dont_dex=get(29),
            fevrier_total=get(30),    fevrier_dont_dex=get(31),
            mars_total=get(32),       mars_dont_dex=get(33),
            avril_total=get(34),      avril_dont_dex=get(35),
            mai_total=get(36),        mai_dont_dex=get(37),
            juin_total=get(38),       juin_dont_dex=get(39),
            juillet_total=get(40),    juillet_dont_dex=get(41),
            aout_total=get(42),       aout_dont_dex=get(43),
            septembre_total=get(44),  septembre_dont_dex=get(45),
            octobre_total=get(46),    octobre_dont_dex=get(47),
            novembre_total=get(48),   novembre_dont_dex=get(49),
            decembre_total=get(50),   decembre_dont_dex=get(51),
        )
        records.append(record)

    BudgetRecord.objects.bulk_create(records)
    return len(records)