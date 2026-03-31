from django.urls import path
from .views import (
    ExcelUploadView,
    UploadListView,
    BudgetRecordListView,
    RecapParRegionView,
    RecapParFamilleView,
    RecapParActiviteView,
    RecapGlobalView,
    RecapFamilleParActiviteView,
    BudgetRecordPDFView,
)

urlpatterns = [
    # Upload
    path('upload/',        ExcelUploadView.as_view(),      name='excel-upload'),
    path('uploads/',       UploadListView.as_view(),        name='upload-list'),
    path('records/',       BudgetRecordListView.as_view(),  name='record-list'),

    # Recaps
    path('recap/region/',   RecapParRegionView.as_view(),  name='recap-region'),
    path('recap/famille/',  RecapParFamilleView.as_view(), name='recap-famille'),
    path('recap/activite/', RecapParActiviteView.as_view(),name='recap-activite'),
    path('recap/global/',   RecapGlobalView.as_view(),     name='recap-global'),
    path('recap/famille-par-activite/', RecapFamilleParActiviteView.as_view()),
    path('export/pdf/<int:pk>/', BudgetRecordPDFView.as_view(), name='budget-pdf'),
]
