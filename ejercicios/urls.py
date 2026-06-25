from django.urls import path
from . import views

# ¡ESTA LÍNEA ES CRUCIAL!
app_name = 'ejercicios'

urlpatterns = [
    # Ruta para procesar el formulario del modal del docente
    path('clase/<int:clase_id>/crear/', views.crear_ejercicio, name='crear_ejercicio'),
]