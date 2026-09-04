from django.urls import path
from . import views

app_name = 'clase'

urlpatterns = [
    path('', views.index, name='index'),
    path('crear/', views.crear_clase, name='crear_clase'),
    path('editar/<int:clase_id>/', views.editar_clase, name='editar_clase'),
    path('eliminar/<int:clase_id>/', views.eliminar_clase, name='eliminar_clase'),
    path('detalle/<int:clase_id>/', views.detalle_clase, name='detalle_clase'),
]