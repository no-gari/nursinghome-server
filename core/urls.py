from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('facilities/<str:code>/', views.facility_detail, name='facility_detail'),
]

