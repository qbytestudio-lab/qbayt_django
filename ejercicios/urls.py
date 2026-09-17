from django.urls import path

from . import views


app_name = 'ejercicios'


urlpatterns = [
    path('crear/quiz/<int:clase_id>/', views.crear_quiz, name='crear_quiz'),
    path('crear/juego/<int:clase_id>/', views.crear_juego, name='crear_juego'),
    path('crear/texto/<int:clase_id>/', views.crear_texto, name='crear_texto'),
    path('crear/completar/<int:clase_id>/', views.crear_completar, name='crear_completar'),
    path('calificar/<int:intento_id>/', views.calificar_ejercicio, name='calificar_ejercicio'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/eliminar/', views.eliminar_ejercicio, name='eliminar_ejercicio'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/docente/', views.detalle_ejercicio_docente, name='detalle_ejercicio_docente'),
    path('intento/<int:intento_id>/rechazar/', views.reenviar_ejercicio, name='reenviar_ejercicio'),
    path('ejercicio/<int:ejercicio_id>/toggle/', views.toggle_estado_ejercicio, name='toggle_estado_ejercicio'),
    path('clase/<int:clase_id>/crear-entrenamiento/',views.crear_entrenamiento_auditivo, name='crear_entrenamiento_auditivo'),
    path('resolver-entrenamiento/<int:clase_id>/<int:ejercicio_id>/',views.resolver_entrenamiento_auditivo,name='resolver_entrenamiento_auditivo'),
    path('guardar-practica-auditiva/<int:ejercicio_id>/',views.guardar_practica_auditiva,name='guardar_practica_auditiva'),
    path('reporte-debilidades/<int:clase_id>/',views.reporte_debilidades,name='reporte_debilidades'),
    path('debilidades/', views.debilidades_global, name='debilidades_global'),
    path('debilidades/exportar-pdf/',views.exportar_debilidades_pdf,name='exportar_debilidades_pdf'),
    # Modo libre
    path('practicar/', views.practicar, name='practicar'),
    path('practicar/sesion/', views.practicar_sesion, name='practicar_sesion'),
    path('practicar/guardar/', views.guardar_practica_libre, name='guardar_practica_libre'),
    # Entrenamiento avanzado
    path('clase/<int:clase_id>/crear-avanzado/<str:subtipo>/',views.crear_entrenamiento_avanzado,name='crear_entrenamiento_avanzado'),
    path('resolver-avanzado/<int:clase_id>/<int:ejercicio_id>/',views.resolver_entrenamiento_avanzado,name='resolver_entrenamiento_avanzado'),
    path('guardar-practica-avanzada/<int:ejercicio_id>/',views.guardar_practica_avanzada,name='guardar_practica_avanzada'),
    ]