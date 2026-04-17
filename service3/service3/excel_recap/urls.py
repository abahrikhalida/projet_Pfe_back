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
    path('budget/nouveau-projet/', CreateBudgetRecordManuelView.as_view(), name='create-budget-manuel'),
    path('budget/projet/<str:code_division>/', BudgetRecordByCodeDivisionView.as_view()),
    # validation
    path('budget/soumettre/<int:record_id>/',                  SoumettreProjetView.as_view()),
    path('budget/valider/directeur-region/<int:record_id>/',   ValiderDirecteurRegionView.as_view()),
    path('budget/valider/chef/<int:record_id>/',               ValiderChefView.as_view()),
    path('budget/valider/directeur/<int:record_id>/',          ValiderDirecteurView.as_view()),
    path('budget/valider/divisionnaire/<int:record_id>/',      ValiderDivisionnnaireView.as_view()),
    path('budget/statut/<int:record_id>/', StatutValidationView.as_view()),

]
