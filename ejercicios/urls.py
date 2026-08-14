from django.urls import path

from . import views


app_name = 'ejercicios'


urlpatterns = [
    path('crear/<int:clase_id>/',views.crear_ejercicio,name='crear_ejercicio'),
    path(
        'crear/quiz/<int:clase_id>/',
        views.crear_quiz,
        name='crear_quiz'
    ),

    path(
        'crear/imagen-quiz/<int:clase_id>/',
        views.crear_imagen_quiz,
        name='crear_imagen_quiz'
    ),

    path(
        'crear/juego/<int:clase_id>/',
        views.crear_juego,
        name='crear_juego'
    ),

    path(
        'crear/texto/<int:clase_id>/',
        views.crear_texto,
        name='crear_texto'
    ),

    path(
        'crear/verdadero-falso/<int:clase_id>/',
        views.crear_verdadero_falso,
        name='crear_verdadero_falso'
    ),

    path(
        'crear/completar/<int:clase_id>/',
        views.crear_completar,
        name='crear_completar'
    ),

    path(
        'calificar/<int:intento_id>/',
        views.calificar_ejercicio,
        name='calificar_ejercicio'
    ),
    
]