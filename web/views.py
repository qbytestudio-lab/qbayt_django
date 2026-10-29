from datetime import datetime, timedelta
import io
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.db.models import Count, Q, Avg
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor
from web.models import Perfil, Certificado
from web.utils import enviar_correo_verificacion
from web.tokens import generador_token_verificacion
from docente.models import Clase, SolicitudClase
from ejercicios.models import Ejercicio, IntentoEjercicio
from notificaciones.services import crear_notificacion
def index(request):
    return render(request, 'web/index.html')
@login_required
def inicio(request):
    clases_teoria = Clase.objects.filter(categoria_tema='armonia')
    clases_auditivo = Clase.objects.filter(categoria_tema='ritmo')
    clases_instrumento = Clase.objects.filter(categoria_tema='melodia')
    if request.user.perfil.rol == 'estudiante':
        clases_activas = request.user.clases_estudiante.count()
        ejercicios_completados = IntentoEjercicio.objects.filter(estudiante=request.user, aprobado=True).values('ejercicio').distinct().count()
        ejercicios_pendientes = Ejercicio.objects.filter(clase__in=request.user.clases_estudiante.all()).exclude(intentos__estudiante=request.user, intentos__aprobado=True).count()
        total_ejercicios = Ejercicio.objects.filter(clase__in=request.user.clases_estudiante.all()).count()
        progreso_general = round((ejercicios_completados / total_ejercicios) * 100) if total_ejercicios > 0 else 0
    elif request.user.perfil.rol == 'docente':
        clases_activas = Clase.objects.filter(docente=request.user).count()
        total_estudiantes = sum(c.estudiantes.count() for c in Clase.objects.filter(docente=request.user))
        ejercicios_completados, ejercicios_pendientes, progreso_general = 0, 0, 0
    else:
        clases_activas, ejercicios_completados, ejercicios_pendientes, progreso_general = Clase.objects.count(), 0, 0, 0
    context = {'cursos_teoria': clases_teoria, 'cursos_auditivo': clases_auditivo, 'cursos_instrumento': clases_instrumento, 'clases_activas': clases_activas, 'ejercicios_completados': ejercicios_completados, 'ejercicios_pendientes': ejercicios_pendientes, 'progreso_general': progreso_general}
    return render(request, 'web/inicio.html', context)
@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante': return redirect('inicio')
    return render(request, 'perfil_estudiante.html')
@login_required
def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_superuser: return redirect('admin_dashboard')
    if request.method == 'POST':
        username, password = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, f'¡Bienvenido administrador {user.username}!')
            return redirect('admin_dashboard')
        else: messages.error(request, 'Credenciales inválidas o no tienes permisos.')
    return render(request, 'admin/login.html')
def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')
@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def admin_dashboard(request):
    total_usuarios = User.objects.count()
    ultimos_usuarios = User.objects.order_by('-date_joined')[:10]
    return render(request, 'admin/dashboard.html', {'total_usuarios': total_usuarios, 'ultimos_usuarios': ultimos_usuarios})
@login_required
def perfil_administrador(request):
    if request.user.perfil.rol != 'administrador': return redirect('inicio')
    return render(request, 'perfil_admin.html')
def registro(request):
    if request.method == 'POST':
        first_name, last_name, username, email = request.POST.get('first_name'), request.POST.get('last_name'), request.POST.get('username'), request.POST.get('email')
        password1, password2, rol = request.POST.get('password1'), request.POST.get('password2'), request.POST.get('rol', 'estudiante')
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('registro')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return redirect('registro')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ese correo ya está registrado.')
            return redirect('registro')
        user = User.objects.create_user(username=username, email=email, password=password1, first_name=first_name, last_name=last_name, is_