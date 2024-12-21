from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_file, name='upload'),
    path('', views.horse_analysis, name='horse_analysis'),
    path('horse/<str:horse_name>/', views.horse_detail, name='horse_detail'),
]