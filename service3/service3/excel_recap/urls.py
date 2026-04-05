from django.urls import path
from .views import *

urlpatterns = [
    # Upload
    path('upload/',        ExcelUploadView.as_view(),      name='excel-upload'),
    path('uploads/',       UploadListView.as_view(),        name='upload-list'),
    path('records/',       BudgetRecordListView.as_view(),  name='record-list'),

    # Recaps
    path('region/',   RecapParRegionView.as_view(),  name='recap-region'),
    path('famille/',  RecapParFamilleView.as_view(), name='recap-famille'),
    path('activite/', RecapParActiviteView.as_view(),name='recap-activite'),
    path('global/',   RecapGlobalView.as_view(),     name='recap-global'),
    path('famille-par-activite/', RecapFamilleParActiviteView.as_view()),
    path('export/pdf/<int:pk>/', BudgetRecordPDFView.as_view(), name='budget-pdf'),
    path('region-famille/', RecapRegionFamilleView.as_view(), name='recap-region-famille'),
    path('verification/', VerificationCalculsView.as_view(), name='verification-calculs'),
]
