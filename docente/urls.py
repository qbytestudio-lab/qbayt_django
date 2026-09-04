from django.urls import path
from . import views

urlpatterns = [
    path('perfil/', views.perfil_docente, name='perfil_docente'),
    path('clase/<int:clase_id>/agregar/', views.agregar_estudiante, name='agregar_estudiante'),
    path('clase/<int:clase_id>/estudiante/<int:estudiante_id>/eliminar/', views.eliminar_estudiante_clase, name='eliminar_estudiante_clase'),
    path('solicitud/<int:solicitud_id>/aceptar/', views.aceptar_solicitud, name='aceptar_solicitud'),
    path('solicitud/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
    path('clase/<int:clase_id>/anuncio/', views.crear_anuncio, name='crear_anuncio'),
    path('clase/<int:clase_id>/anuncio/<int:anuncio_id>/eliminar/', views.eliminar_anuncio, name='eliminar_anuncio'),
    path('clase/<int:clase_id>/generar_pdf/', views.generar_reporte_pdf, name='generar_reporte_pdf'),
    path('clase/<int:clase_id>/estadisticas/', views.estadisticas_clase, name='estadisticas_clase'),
    path('clase/<int:clase_id>/expulsar/<int:estudiante_id>/', views.expulsar_estudiante_clase, name='expulsar_estudiante_clase'),
    
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/editar/', views.editar_ejercicio, name='editar_ejercicio'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/eliminar/', views.eliminar_ejercicio, name='eliminar_ejercicio'),
    path('mis-clases/', views.mis_clases, name='mis_clases'),
]