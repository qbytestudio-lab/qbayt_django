from django.urls import path

from . import views


app_name = 'ejercicios'


urlpatterns = [
    path('crear/quiz/<int:clase_id>/', views.crear_quiz, name='crear_quiz'),
    path('clase/<int:clase_id>/crear-video-quiz/', views.crear_video_quiz, name='crear_video_quiz'),
    path('crear/juego/<int:clase_id>/', views.crear_juego, name='crear_juego'),
    path('crear/texto/<int:clase_id>/', views.crear_texto, name='crear_texto'),
    path('crear/verdadero-falso/<int:clase_id>', views.crear_verdadero_falso, name='crear_verdadero_falso'),
    path('crear/completar/<int:clase_id>/', views.crear_completar, name='crear_completar'),
    path('calificar/<int:intento_id>/', views.calificar_ejercicio, name='calificar_ejercicio'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/eliminar/', views.eliminar_ejercicio, name='eliminar_ejercicio'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/docente/', views.detalle_ejercicio_docente, name='detalle_ejercicio_docente'),
    path('intento/<int:intento_id>/rechazar/', views.reenviar_ejercicio, name='reenviar_ejercicio'),
    ]