# notificaciones/urls.py
from django.urls import path
from . import views

app_name = 'notificaciones'
urlpatterns = [
    path('', views.listar_notificaciones, name='lista'),
    path('marcar-leida/<int:notificacion_id>/', views.marcar_leida, name='marcar_leida'),
    path('marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
    path('api/no-leidas/', views.obtener_no_leidas, name='api_no_leidas'),
]