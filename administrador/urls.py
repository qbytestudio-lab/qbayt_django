from django.urls import path
from . import views

app_name = 'administrador'


urlpatterns = [
    path('login/', views.login_admin, name='login_admin'),
    path('panel/', views.panel_admin, name='panel_admin'),
    path('suspender/<int:user_id>/', views.suspender_usuario, name='suspender_usuario'),
    path('eliminar/<int:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('practicas/', views.gestionar_practicas, name='gestionar_practicas'),
    path('practicas/crear/', views.crear_pregunta_practica, name='crear_pregunta_practica'),
    path('practicas/eliminar/<int:pregunta_id>/', views.eliminar_practica, name='eliminar_practica'),
]