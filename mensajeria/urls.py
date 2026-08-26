from django.urls import path
from . import views

app_name = 'mensajeria'

urlpatterns = [
    path('', views.listar_conversaciones, name='lista'),
    path('clase/<int:clase_id>/contactos/', views.contactos_clase, name='contactos_clase'),
    path('iniciar/<int:usuario_id>/', views.iniciar_conversacion, name='iniciar'),
    path('conversacion/<int:conversacion_id>/', views.detalle_conversacion, name='detalle'),
]