from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_admin, name='login_admin'),
    path('panel/', views.panel_admin, name='panel_admin'),
    path('suspender/<int:user_id>/', views.suspender_usuario, name='suspender_usuario'),
    path('eliminar/<int:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),
]