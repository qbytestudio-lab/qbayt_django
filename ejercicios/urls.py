from django.urls import path
from . import views

urlpatterns = [
    # Ruta para crear el ejercicio asociado a una clase específica
    path('clase/<int:clase_id>/crear-ejercicio/', views.crear_ejercicio, name='crear_ejercicio'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/editar/', views.editar_ejercicio, name='editar_ejercicio'),
    path('clase/<int:clase_id>/ejercicio/<int:ejercicio_id>/eliminar/', views.eliminar_ejercicio, name='eliminar_ejercicio'),
]
