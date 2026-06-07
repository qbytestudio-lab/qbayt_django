from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('registro/', views.registro, name='registro'),
    path('ingreso/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('inicio/', views.inicio, name='inicio'),
    path('perfil/estudiante/', views.perfil_estudiante, name='perfil_estudiante'),
    path('perfil/docente/', views.perfil_docente, name='perfil_docente'),
    path('perfil/admin/', views.perfil_administrador, name='perfil_administrador'),
]