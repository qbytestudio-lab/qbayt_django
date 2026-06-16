from django.urls import path
from . import views

urlpatterns = [
    path('perfil/', views.perfil_estudiante, name='perfil_estudiante'),
    path('unirse-clase/', views.unirse_clase, name='unirse_clase'),
    path('solicitar-clase/', views.solicitar_clase, name='solicitar_clase'),
    path('salir-clase/<int:clase_id>/', views.salir_clase, name='salir_clase'),
    path('explorar-clases/', views.explorar_clases, name='explorar_clases'),
    path('clase/<int:clase_id>/', views.detalle_clase_estudiante, name='detalle_clase_estudiante'),

    path('clase/<int:clase_id>/', views.detalle_clase_estudiante, name='detalle_clase_estudiante'),
    path('actividad/<int:actividad_id>/', views.detalle_actividad_estudiante, name='detalle_actividad_estudiante'),
    path('actividad/<int:actividad_id>/responder/', views.responder_actividad, name='responder_actividad'),
]