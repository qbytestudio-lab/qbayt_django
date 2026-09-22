"""
URL configuration for qbyt project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.urls')),
    path('docente/', include('docente.urls')),
    path('estudiante/', include(('estudiante.urls', 'estudiante'), namespace='estudiante')),
    path('clase/', include('clase.urls')),
    path('ejercicios/', include('ejercicios.urls')),

    # ═══════════════════════════════════════════
    # RECUPERAR CONTRASEÑA
    # ═══════════════════════════════════════════
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.txt',
        html_email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # ═══════════════════════════════════════════
    # OTRAS RUTAS
    # ═══════════════════════════════════════════
    path('notificaciones/', include('notificaciones.urls')),
    path('mensajeria/', include('mensajeria.urls')),
    path('accounts/', include('allauth.urls')),
]

# ═══════════════════════════════════════════
# SERVIR ARCHIVOS DE MEDIA Y STATIC EN DESARROLLO
# ═══════════════════════════════════════════
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)