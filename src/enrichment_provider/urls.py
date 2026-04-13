from django.urls import path
from . import views

urlpatterns = [
    path('enrichments/', views.get_enrichments, name='get_enrichments'),
    path('enrichments/types/', views.get_enrichment_types, name='get_enrichment_types'),
]
