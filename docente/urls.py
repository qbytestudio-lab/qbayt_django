from django.urls import path
from . import views

urlpatterns = [
    path('perfil/', views.perfil_docente, name='perfil_docente'),
    path('crear-clase/', views.crear_clase, name='crear_clase'),
    path('clase/<int:clase_id>/', views.detalle_clase, name='detalle_clase'),
    path('clase/<int:clase_id>/eliminar/', views.eliminar_clase, name='eliminar_clase'),
    path('clase/<int:clase_id>/agregar/', views.agregar_estudiante, name='agregar_estudiante'),
    path('clase/<int:clase_id>/estudiante/<int:estudiante_id>/eliminar/', views.eliminar_estudiante_clase, name='eliminar_estudiante_clase'),
    path('solicitud/<int:solicitud_id>/aceptar/', views.aceptar_solicitud, name='aceptar_solicitud'),
    path('solicitud/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
]