from django.urls import path, include
from django.shortcuts import redirect
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
    
    # ============================================
    # OTRAS RUTAS
    # ============================================
    path('progreso/', views.progreso, name='progreso'),
    path('calendario/', views.calendario, name='calendario'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/logout/', views.admin_logout_view, name='admin_logout'),
    path('clase/<int:clase_id>/progreso/', views.progreso_clase_detalle, name='progreso_detalle_clase'),
    path('certificados/', views.certificados, name='certificados'),
    path('certificados/descargar/<int:clase_id>/', views.descargar_certificado, name='descargar_certificado'),
]