from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views

# DRF 라우터 설정
router = DefaultRouter()
router.register(r'facilities', views.FacilityViewSet)

app_name = 'core'

urlpatterns = [
    # Django 템플릿 뷰
    path('', views.chatbot_view, name='chatbot'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:chatbot'), name='logout'),
    path('facility/<str:code>/', views.facility_detail, name='facility_detail'),

    # DRF API
    path('api/', include(router.urls)),
    path('api/chat/', views.ChatbotAPI.as_view(), name='chatbot_api'),
    path('api/initialize-rag/', views.initialize_rag, name='initialize_rag'),
]
