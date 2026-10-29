from django.urls import path
from . import views
app_name = 'docente'
urlpatterns = [
    path('docente/perfil/', views.perfil_docente, name='perfil_docente'),
    path('docente/clase/<int:clase_id>/agregar/', views.agregar_estudiante, name='agregar_estudiante'),
    path('docente/clase/<int:clase_id>/estudiante/<int:estudiante_id>/eliminar/', views.eliminar_estudiante_clase, name='eliminar_estudiante_clase'),
    path('docente/solicitud/<int:solicitud_id>/aceptar/', views.aceptar_solicitud, name='aceptar_solicitud'),
    path('docente/solicitud/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
    path('docente/clase/<int:clase_id>/anuncio/', views.crear_anuncio, name='crear_anuncio'),
    path('docente/clase/<int:clase_id>/anuncio/<int:anuncio_id>/eliminar/', views.eliminar_anuncio, name='eliminar_anuncio'),
    path('docente/clase/<int:clase_id>/generar_pdf/', views.generar_reporte_pdf, name='generar_reporte_pdf'),
    path('docente/clase/<int:clase_id>/estadisticas/', views.estadisticas_clase, name='estadisticas_clase'),
    path('docente/clase/<int:clase_id>/expulsar/<int:estudiante_id>/', views.expulsar_estudiante_clase, name='expulsar_estudiante_clase'),
    path('docente/clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/editar/', views.editar_ejercicio, name='editar_ejercicio'),
    path('docente/clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/eliminar/', views.eliminar_ejercicio, name='eliminar_ejercicio'),
    path('docente/mis-clases/', views.mis_clases, name='mis_clases'),
    # notas del estudiante en una clase
    path('docente/clase/<int:clase_id>/estudiante/<int:estudiante_id>/notas/', views.notas_estudiante, name='notas_estudiante'),
    path('docente/biblioteca-recursos/', views.biblioteca_recursos, name='biblioteca_recursos'),
    path('docente/biblioteca-recursos/crear/', views.crear_recurso, name='crear_recurso'),
    path('docente/biblioteca-recursos/eliminar/<int:recurso_id>/', views.eliminar_recurso, name='eliminar_recurso'),
    path('docente/biblioteca-recursos/editar/<int:recurso_id>/', views.editar_recurso, name='editar_recurso'),
    path('docente/biblioteca-recursos/vista/<int:recurso_id>/', views.incrementar_vista_recurso, name='incrementar_vista_recurso'),
]