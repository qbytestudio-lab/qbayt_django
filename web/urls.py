from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('registro/', views.registro, name='registro'),
    path('ingreso/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('inicio/', views.inicio, name='inicio'),
    path('perfil/admin/', views.perfil_administrador, name='perfil_administrador'),
    # --- RUTAS AGREGADAS PARA EL SELF-CRUD ---
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/eliminar/', views.eliminar_perfil, name='eliminar_perfil'),
    path('cursos/', views.cursos, name='cursos'),
    path('mis-clases/', views.mis_clases, name='mis_clases'),
    path('progreso/', views.progreso, name='progreso'),
    path('certificados/', views.certificados, name='certificados'),
    path('curso/<int:curso_id>/agregar/', views.agregar_curso, name='agregar_curso'),
    path('curso/<int:curso_id>/eliminar/', views.eliminar_curso, name='eliminar_curso'),
]