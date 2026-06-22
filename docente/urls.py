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
    path('clase/<int:clase_id>/anuncio/', views.crear_anuncio, name='crear_anuncio'),
    path('clase/<int:clase_id>/leccion/', views.crear_leccion, name='crear_leccion'),
    path('clase/<int:clase_id>/leccion/<int:leccion_id>/eliminar/', views.eliminar_leccion, name='eliminar_leccion'),
    path('clase/<int:clase_id>/anuncio/<int:anuncio_id>/eliminar/', views.eliminar_anuncio, name='eliminar_anuncio'),
    path('clase/<int:clase_id>/leccion/<int:leccion_id>/', views.detalle_leccion, name='detalle_leccion'),
    path('clase/<int:clase_id>/leccion/<int:leccion_id>/actividad/', views.crear_actividad, name='crear_actividad'),
    path('clase/<int:clase_id>/leccion/<int:leccion_id>/actividad/<int:actividad_id>/', views.detalle_actividad, name='detalle_actividad'),
    path('actividad/<int:actividad_id>/pregunta/', views.crear_pregunta, name='crear_pregunta'),
    path('clase/<int:clase_id>/editar/', views.editar_clase, name='editar_clase'),
    path('clase/<int:clase_id>/eliminar/', views.eliminar_clase, name='eliminar_clase'),
]