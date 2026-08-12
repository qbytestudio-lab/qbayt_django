from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('registro/', views.registro, name='registro'),
    path('ingreso/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('inicio/', views.inicio, name='inicio'),
    path('admperfil_administrador/', views.perfil_administrador, name='perfil_administrador'),
    # --- RUTAS AGREGADAS PARA EL SELF-CRUD ---
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/eliminar/', views.eliminar_perfil, name='eliminar_perfil'),
    path('cursos/', views.cursos, name='cursos'),
    path('mis-clases/', views.mis_clases, name='mis_clases'),
    path('progreso/', views.progreso, name='progreso'),
    path('certificados/', views.certificados, name='certificados'),
    path('curso/<int:curso_id>/agregar/', views.agregar_curso, name='agregar_curso'),
    path('curso/<int:curso_id>/eliminar/', views.eliminar_curso, name='eliminar_curso'),
    path('calendario/', views.calendario, name='calendario'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/logout/', views.admin_logout_view, name='admin_logout'),
    path('crear-curso/',views.crear_curso, name='crear_curso'),
    path('cursos/eliminar-propio/<int:curso_id>/', views.eliminar_curso_propio, name='eliminar_curso_propio'),  # ✅ NUEVO
    path('agregar_curso/<int:curso_id>/', views.agregar_curso, name='agregar_curso'),
    path('detalle_curso/<int:curso_id>/', views.detalle_curso, name='detalle_curso'),
    path('curso/<int:curso_id>/continuar/', views.continuar_curso, name='continuar_curso'),  # ✅ NUEVA URL
    
]
