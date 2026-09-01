from django.urls import path
from . import views

app_name = 'estudiante'

urlpatterns = [
    # Al dejarlo vacío '', se combina con 'perfil/estudiante/' de la app web
    path('', views.perfil_estudiante, name='perfil_estudiante'),
    path('unirse-clase/', views.unirse_clase, name='unirse_clase'),
    path('solicitar-clase/', views.solicitar_clase, name='solicitar_clase'),
    path('salir-clase/<int:clase_id>/', views.salir_clase, name='salir_clase'),
    path('explorar-clases/', views.explorar_clases, name='explorar_clases'),
    path('clase/<int:clase_id>/', views.detalle_clase_estudiante, name='detalle_clase_estudiante'),
    path('mis-calificaciones/', views.mis_calificaciones_estudiante, name='mis_calificaciones_estudiante'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/resolver/', views.resolver_ejercicio, name='resolver_ejercicio'),
    path('subir-foto-perfil/', views.subir_foto_perfil, name='subir_foto_perfil'),
    path('subir-banner/', views.subir_banner, name='subir_banner'),
    # resolver_video_quiz y enviar_respuesta_video_quiz son las nuevas rutas para el video quiz
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/resolver-video/',views.resolver_video_quiz,name='resolver_video_quiz'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/enviar-video/', views.enviar_respuesta_video_quiz,name='enviar_respuesta_video_quiz'),
]