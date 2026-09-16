from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from web.models import Perfil
from django.contrib.auth.decorators import login_required, user_passes_test
from docente.models import Clase, SolicitudClase
from django.shortcuts import get_object_or_404
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg
from ejercicios.models import Ejercicio, IntentoEjercicio
from clase.models import Clase
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import io
from web.utils import enviar_correo_verificacion
from web.tokens import generador_token_verificacion
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from web.models import Perfil, Certificado
from django.views.decorators.http import require_POST


def index(request):
    return render(request, 'web/index.html')

@login_required
def inicio(request):
    from clase.models import Clase
    from ejercicios.models import Ejercicio, IntentoEjercicio
    
    # Obtener clases según categoría
    clases_teoria = Clase.objects.filter(categoria_tema='armonia')
    clases_auditivo = Clase.objects.filter(categoria_tema='ritmo')
    clases_instrumento = Clase.objects.filter(categoria_tema='melodia')
    
    # Stats dinámicos
    if request.user.perfil.rol == 'estudiante':
        # Clases activas del estudiante
        clases_activas = request.user.clases_estudiante.count()
        
        # Ejercicios completados (aprobados)
        ejercicios_completados = IntentoEjercicio.objects.filter(
            estudiante=request.user,
            aprobado=True
        ).values('ejercicio').distinct().count()
        
        # Ejercicios pendientes
        ejercicios_pendientes = Ejercicio.objects.filter(
            clase__in=request.user.clases_estudiante.all()
        ).exclude(
            intentos__estudiante=request.user,
            intentos__aprobado=True
        ).count()
        
        # Progreso general
        total_ejercicios = Ejercicio.objects.filter(
            clase__in=request.user.clases_estudiante.all()
        ).count()
        
        progreso_general = 0
        if total_ejercicios > 0:
            progreso_general = round((ejercicios_completados / total_ejercicios) * 100)
        
    elif request.user.perfil.rol == 'docente':
        # Clases del docente
        clases_activas = Clase.objects.filter(docente=request.user).count()
        
        # Total de estudiantes
        total_estudiantes = sum(c.estudiantes.count() for c in Clase.objects.filter(docente=request.user))
        
        ejercicios_completados = 0
        ejercicios_pendientes = 0
        progreso_general = 0
        
    else:
        clases_activas = Clase.objects.count()
        ejercicios_completados = 0
        ejercicios_pendientes = 0
        progreso_general = 0
    
    context = {
        'cursos_teoria': clases_teoria,
        'cursos_auditivo': clases_auditivo,
        'cursos_instrumento': clases_instrumento,
        'clases_activas': clases_activas,
        'ejercicios_completados': ejercicios_completados,
        'ejercicios_pendientes': ejercicios_pendientes,
        'progreso_general': progreso_general,
    }
    
    return render(request, 'web/inicio.html', context)

@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    return render(request, 'perfil_estudiante.html')

@login_required
def admin_login_view(request):
    """Login exclusivo para administradores"""
    # Si ya está autenticado como admin, redirigir al dashboard
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, f'¡Bienvenido administrador {user.username}!')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Credenciales inválidas o no tienes permisos.')
    
    return render(request, 'admin/login.html')


def admin_logout_view(request):
    """Cerrar sesión del administrador"""
    logout(request)
    return redirect('admin_login')


@user_passes_test(lambda u: u.is_superuser, login_url='admin_login')
def admin_dashboard(request):
    """Dashboard principal del admin"""
    
    # Estadísticas
    total_usuarios = User.objects.count()
    ultimos_usuarios = User.objects.order_by('-date_joined')[:10]
    
    context = {
        'total_usuarios': total_usuarios,
        'ultimos_usuarios': ultimos_usuarios,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
def perfil_administrador(request):
    if request.user.perfil.rol != 'administrador':
        return redirect('inicio')
    return render(request, 'perfil_admin.html')

def registro(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        rol = request.POST.get('rol', 'estudiante')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('registro')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return redirect('registro')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ese correo ya está registrado.')
            return redirect('registro')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )

        Perfil.objects.create(user=user, rol=rol)

        try:
            enviar_correo_verificacion(request, user)   # 👈 ESTA LÍNEA
            messages.success(request, f'Te enviamos un correo a {email}...')
        except Exception as e:
            messages.warning(request, f'Cuenta creada pero no se pudo enviar el correo: {e}')

        return redirect('login')

    return render(request, 'web/registro.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 🔒 Bloquear si la cuenta no está verificada
            if not user.is_active:
                messages.error(
                    request,
                    'Debes verificar tu correo antes de iniciar sesión. Revisa tu bandeja.'
                )
                return redirect('login')

            login(request, user)
            return redirect('inicio')

        # Verificar si existe pero está inactivo
        try:
            u = User.objects.get(username=username)
            if not u.is_active:
                messages.warning(
                    request,
                    'Tu cuenta existe pero aún no está verificada. Revisa tu correo.'
                )
                return redirect('login')
        except User.DoesNotExist:
            pass

        messages.error(request, 'Usuario o contraseña incorrectos.')
        return redirect('login')

    return render(request, 'web/login.html')

def logout_view(request):
    logout(request)
    return redirect('index')
# Al final de web/views.py

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        usuario = request.user
        usuario.username = request.POST.get('username')
        usuario.email = request.POST.get('email')
        usuario.first_name = request.POST.get('first_name')
        usuario.last_name = request.POST.get('last_name')
        usuario.save() # Guarda los cambios en MySQL
        
        messages.success(request, '¡Tu perfil ha sido actualizado correctamente!')
        
        # Redirección inteligente según el rol del usuario que edita
        if usuario.perfil.rol == 'estudiante':
            return redirect('perfil_estudiante')
        elif usuario.perfil.rol == 'docente':
            return redirect('perfil_docente')
        else:
            return redirect('perfil_administrador')
        
    return redirect('inicio')
@login_required
def eliminar_perfil(request):
    usuario = request.user
    logout(request) # Cerramos la sesión antes de borrarlo para que Django no se enrede
    usuario.delete() # Al borrar el User, el CASCADE borra también su Perfil automáticamente
    messages.success(request, 'Tu cuenta ha sido eliminada permanentemente.')
    return redirect('index')


@login_required
def progreso(request):
    
    # Obtener clases del estudiante
    clases = request.user.clases_estudiante.all()
    
    # ============================================
    # MISMAS VARIABLES QUE INICIO
    # ============================================
    
    # Ejercicios completados (con al menos un intento)
    ejercicios_completados_ids = IntentoEjercicio.objects.filter(
        estudiante=request.user
    ).values_list('ejercicio_id', flat=True).distinct()
    
    ejercicios_completados = ejercicios_completados_ids.count()
    
    # Ejercicios pendientes (sin intentos)
    pendientes = Ejercicio.objects.filter(
        clase__in=clases
    ).exclude(id__in=ejercicios_completados_ids).select_related('clase')
    
    ejercicios_pendientes = pendientes.count()
    
    # Total de ejercicios
    total_ejercicios = Ejercicio.objects.filter(clase__in=clases).count()
    
    # Progreso general
    progreso_general = 0
    if total_ejercicios > 0:
        progreso_general = round((ejercicios_completados / total_ejercicios) * 100)
    
    # ============================================
    # PROGRESO POR CLASE
    # ============================================
    progreso_clases = []
    for clase in clases:
        total_clase = Ejercicio.objects.filter(clase=clase).count()
        completados_clase = IntentoEjercicio.objects.filter(
            estudiante=request.user,
            ejercicio__clase=clase
        ).values('ejercicio').distinct().count()
        
        porcentaje = round((completados_clase / total_clase) * 100) if total_clase > 0 else 0
        
        progreso_clases.append({
            'clase': clase,
            'total': total_clase,
            'completados': completados_clase,
            'porcentaje': porcentaje,
        })
    
    # ============================================
    # RENDIMIENTO PARA LA GRÁFICA (NUEVO)
    # ============================================
    intentos_estudiante = IntentoEjercicio.objects.filter(
        estudiante=request.user, 
        calificacion__isnull=False
    )

    rendimiento_por_tipo = intentos_estudiante.values('ejercicio__tipo').annotate(
        promedio_nota=Avg('calificacion')
    )

    tipo_nombres = {
        'quiz': 'Quiz',
        'imagen_quiz': 'Quiz con imagen',
        'juego': 'Juego',
        'texto': 'Texto',
        'verdadero_falso': 'Verdadero / Falso',
        'completar': 'Completar'
    }

    categorias = [tipo_nombres.get(item['ejercicio__tipo'], item['ejercicio__tipo']) for item in rendimiento_por_tipo]
    promedios = [float(item['promedio_nota']) for item in rendimiento_por_tipo]

    # ============================================
    # ÚLTIMAS ACTIVIDADES
    # ============================================
    actividades_lista = []
    
    # Intentos recientes
    intentos = IntentoEjercicio.objects.filter(
        estudiante=request.user
    ).select_related('ejercicio__clase').order_by('-fecha_envio')[:10]
    
    for intento in intentos:
        actividades_lista.append({
            'titulo': intento.ejercicio.titulo,
            'clase_nombre': intento.ejercicio.clase.nombre,
            'puntaje': intento.calificacion if intento.calificacion else 0,
            'clase_id': intento.ejercicio.clase.id,
        })
    
    # Ejercicios pendientes para la lista
    ejercicios_pendientes_lista = pendientes.order_by('-fecha_creacion')[:5]
    
    for ejercicio in ejercicios_pendientes_lista:
        actividades_lista.append({
            'titulo': ejercicio.titulo,
            'clase_nombre': ejercicio.clase.nombre,
            'puntaje': None,
            'clase_id': ejercicio.clase.id,
        })
    
    context = {
        'clases': clases,
        # Stats - Mismas variables que inicio
        'clases_activas': clases.count(),
        'ejercicios_completados': ejercicios_completados,
        'ejercicios_pendientes': ejercicios_pendientes,
        'progreso_general': progreso_general,
        # Para compatibilidad con template actual
        'total_clases': clases.count(),
        'actividades_completadas': ejercicios_completados,
        'actividades_pendientes': ejercicios_pendientes,
        # Progreso por clase
        'progreso_clases': progreso_clases,
        # Datos para la Gráfica de Rendimiento
        'categorias': categorias,
        'promedios': promedios,
        # Actividades
        'actividades_lista': actividades_lista,
    }
    
    return render(request, 'web/progreso.html', context)
@login_required
def progreso_clase_detalle(request, clase_id):
    # Obtener la clase específica y verificar que el estudiante esté inscrito (o sea suya)
    clase = get_object_or_404(Clase, id=clase_id)
    
    # if clase.nombre.strip().lower() == "acordes mayores":
    #     messages.error(request, "El acceso a la clase 'Acordes mayores' está restringido temporalmente.")
    #     return redirect('progreso') # O a la vista principal de estudiantes
        
    # Todos los ejercicios de esta clase en específico
    ejercicios_clase = Ejercicio.objects.filter(clase=clase)
    total_ejercicios = ejercicios_clase.count()
    
    # IDs de ejercicios de esta clase que el estudiante ha intentado/completado
    completados_ids = IntentoEjercicio.objects.filter(
        estudiante=request.user,
        ejercicio__clase=clase
    ).values_list('ejercicio_id', flat=True).distinct()
    
    ejercicios_completados = completados_ids.count()
    ejercicios_pendientes = total_ejercicios - ejercicios_completados
    
    # Porcentaje de avance en esta clase
    porcentaje_clase = round((ejercicios_completados / total_ejercicios) * 100) if total_ejercicios > 0 else 0
    
    # Gráfica de rendimiento: Promedio de notas por tipo de ejercicio *solo para esta clase*
    intentos_clase = IntentoEjercicio.objects.filter(
        estudiante=request.user,
        ejercicio__clase=clase,
        calificacion__isnull=False
    )
    
    rendimiento_por_tipo = intentos_clase.values('ejercicio__tipo').annotate(
        promedio_nota=Avg('calificacion')
    )
    
    tipo_nombres = {
        'quiz': 'Quiz',
        'imagen_quiz': 'Quiz con imagen',
        'juego': 'Juego',
        'texto': 'Texto',
        'verdadero_falso': 'Verdadero / Falso',
        'completar': 'Completar'
    }
    
    categorias = [tipo_nombres.get(item['ejercicio__tipo'], item['ejercicio__tipo']) for item in rendimiento_por_tipo]
    promedios = [float(item['promedio_nota']) for item in rendimiento_por_tipo]
    
    # Historial de intentos recientes en esta clase
    intentos_recientes = intentos_clase.select_related('ejercicio').order_by('-fecha_envio')[:10]

    context = {
        'clase': clase,
        'total_ejercicios': total_ejercicios,
        'ejercicios_completados': ejercicios_completados,
        'ejercicios_pendientes': ejercicios_pendientes,
        'porcentaje_clase': porcentaje_clase,
        'categorias': categorias,
        'promedios': promedios,
        'intentos_recientes': intentos_recientes,
    }
    
    return render(request, 'web/progreso_detalle_clase.html', context)

@login_required
def certificados(request):
    """
    Vista de certificados del estudiante.
    Solo muestra los certificados que el docente ha emitido oficialmente.
    """
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    certificados_qs = Certificado.objects.filter(
        estudiante=request.user,
        activo=True
    ).select_related('clase', 'docente').order_by('-fecha_emision')

    certificados_lista = []
    for cert in certificados_qs:
        certificados_lista.append({
            'id': cert.clase.id,
            'certificado_id': cert.id,
            'nombre_curso': cert.clase.nombre,
            'instructor': cert.docente.get_full_name() or cert.docente.username,
            'fecha_emision': cert.fecha_emision,
            'codigo_verificacion': cert.codigo_verificacion,
            'horas': cert.horas_completadas,
            'promedio': float(cert.promedio_final),
            'progreso': cert.progreso_final,
        })

    context = {
        'certificados': certificados_lista,
        'total_certificados': len(certificados_lista),
    }

    return render(request, 'web/certificados.html', context)

@login_required
def calendario(request):
    """
    Vista del calendario - con clases próximas a finalizar
    """
    from datetime import date, timedelta

    usuario = request.user

    # Obtener las clases donde el estudiante está inscrito
    clases_inscritas = Clase.objects.filter(estudiantes=usuario)

    # Inicializar contadores
    actividades_pendientes_count = 0
    actividades_completadas_count = 0
    proximos = []
    eventos = []

    # Agregar clases como eventos
    for clase in clases_inscritas:
        fecha = clase.fecha_inicio if clase.fecha_inicio else timezone.now().date()
        eventos.append({
            'title': f'📚 {clase.nombre}',
            'start': fecha.isoformat(),
            'tipo': 'clase',
            'url': f'/estudiante/clase/{clase.id}/',
            'descripcion': f'Clase: {clase.nombre}'
        })

    # Obtener ejercicios de las clases inscritas
    ejercicios = Ejercicio.objects.filter(clase__in=clases_inscritas)

    # Procesar cada ejercicio
    for ejercicio in ejercicios:
        intento_aprobado = IntentoEjercicio.objects.filter(
            estudiante=usuario,
            ejercicio=ejercicio,
            aprobado=True
        ).exists()

        if intento_aprobado:
            actividades_completadas_count += 1
        else:
            actividades_pendientes_count += 1

            if ejercicio.fecha_limite and ejercicio.fecha_limite >= timezone.now():
                proximos.append(ejercicio)

            if ejercicio.fecha_limite:
                eventos.append({
                    'title': f'✏️ {ejercicio.titulo}',
                    'start': ejercicio.fecha_limite.isoformat(),
                    'tipo': 'actividad',
                    'url': f'/estudiante/clase/{ejercicio.clase.id}/',
                })

    if proximos:
        proximos.sort(key=lambda x: x.fecha_limite if x.fecha_limite else timezone.now())

    # ─────────────────────────────────────────────
    # NUEVO: Calcular clases próximas a finalizar
    # ─────────────────────────────────────────────
    hoy = timezone.now().date()
    clases_por_finalizar = []

    for clase in clases_inscritas:
        if clase.fecha_fin:
            dias_restantes = (clase.fecha_fin - hoy).days

            # Mostrar clases que finalizan en los próximos 30 días (incluyendo las ya finalizadas hace poco)
            if dias_restantes <= 30:
                clases_por_finalizar.append({
                    'clase': clase,
                    'dias_restantes': dias_restantes,
                    'fecha_fin': clase.fecha_fin,
                })

    # Ordenar por días restantes (las que vencen primero arriba)
    clases_por_finalizar.sort(key=lambda x: x['dias_restantes'])

    hoy_dt = timezone.now()
    eventos_json = json.dumps(eventos, default=str)
    eventos_hoy = [e for e in eventos if e['start'] == hoy_dt.date().isoformat()]

    context = {
        'eventos_json': eventos_json,
        'eventos_hoy': eventos_hoy,
        'proximos': proximos,
        'total_clases': clases_inscritas.count(),
        'actividades_pendientes': actividades_pendientes_count,
        'actividades_completadas': actividades_completadas_count,
        'hoy': hoy_dt.date(),
        'clases': clases_inscritas,
        'clases_por_finalizar': clases_por_finalizar,   # 👈 NUEVO
    }

    return render(request, 'web/calendario.html', context)

@login_required
def descargar_certificado(request, clase_id):
    """
    Descarga el certificado SOLO si el docente lo ha emitido.
    """
    clase = get_object_or_404(Clase, id=clase_id)

    if request.user not in clase.estudiantes.all():
        messages.error(request, 'No tienes acceso a este certificado.')
        return redirect('certificados')

    # Verificar que exista un certificado emitido
    certificado = Certificado.objects.filter(
        estudiante=request.user,
        clase=clase,
        activo=True
    ).first()

    if not certificado:
        messages.error(
            request,
            'El certificado aún no ha sido emitido por el docente. '
            'Completa el 100% de la clase y espera la emisión.'
        )
        return redirect('certificados')

    promedio = float(certificado.promedio_final)
    fecha_emision = certificado.fecha_emision
    codigo_verificacion = certificado.codigo_verificacion

    # Generar PDF con ReportLab (reusa el código que ya tenías)
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.colors import HexColor

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificado_{clase.nombre}.pdf"'

        p = canvas.Canvas(response, pagesize=landscape(A4))
        width, height = landscape(A4)

        color_principal = HexColor('#1db954')
        color_secundario = HexColor('#7c6fff')
        color_texto = HexColor('#333333')
        color_dorado = HexColor('#FFD700')

        p.setFillColor(HexColor('#f8f9fe'))
        p.rect(0, 0, width, height, fill=1, stroke=0)

        p.setStrokeColor(color_dorado)
        p.setLineWidth(3)
        p.rect(30, 30, width-60, height-60, fill=0, stroke=1)

        p.setStrokeColor(color_principal)
        p.setLineWidth(1)
        p.rect(40, 40, width-80, height-80, fill=0, stroke=1)

        p.setFillColor(color_principal)
        p.setFont("Helvetica-Bold", 28)
        p.drawCentredString(width/2, height-120, "CERTIFICADO")

        p.setFillColor(color_secundario)
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width/2, height-150, "DE FINALIZACIÓN")

        p.setStrokeColor(color_dorado)
        p.setLineWidth(1.5)
        p.line(width/2 - 100, height-165, width/2 + 100, height-165)

        p.setFillColor(color_texto)
        p.setFont("Helvetica", 14)
        p.drawCentredString(width/2, height-200, "Este certificado se otorga a:")

        p.setFillColor(color_secundario)
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width/2, height-240, request.user.get_full_name() or request.user.username)

        p.setFillColor(color_texto)
        p.setFont("Helvetica", 14)
        p.drawCentredString(width/2, height-280, "Por completar exitosamente la clase:")

        p.setFillColor(color_principal)
        p.setFont("Helvetica-Bold", 20)
        p.drawCentredString(width/2, height-315, clase.nombre)

        p.setFillColor(color_texto)
        p.setFont("Helvetica", 12)
        p.drawCentredString(width/2, height-355, f"Docente: {clase.docente.get_full_name() or clase.docente.username}")
        p.drawCentredString(width/2, height-375, f"Fecha: {fecha_emision.strftime('%d de %B de %Y')}")
        p.drawCentredString(width/2, height-395, f"Promedio: {promedio:.1f}")

        # Código de verificación
        p.setFillColor(color_secundario)
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(width/2, 160, f"Código de verificación: {codigo_verificacion}")

        p.setStrokeColor(color_texto)
        p.setLineWidth(0.5)
        p.line(width/2 - 150, 100, width/2 + 150, 100)
        p.setFillColor(color_texto)
        p.setFont("Helvetica", 10)
        p.drawCentredString(width/2, 85, "Director de QBYT")

        p.setFillColor(color_dorado)
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(width/2, 190, "★ QBYT ★")

        p.showPage()
        p.save()
        return response

    except ImportError:
        messages.error(request, 'Error al generar el PDF.')
        return redirect('certificados')

def verificar_correo(request, uidb64, token):
    """
    Vista que activa la cuenta al hacer clic en el link del correo.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and generador_token_verificacion.check_token(user, token):
        if user.is_active:
            messages.info(request, 'Tu cuenta ya estaba verificada. Puedes iniciar sesión.')
            return redirect('login')

        user.is_active = True
        user.save(update_fields=['is_active'])

        messages.success(request, '¡Cuenta verificada con éxito! Ya puedes iniciar sesión.')
        return redirect('login')
    else:
        return render(request, 'web/verificacion_fallida.html')

def reenviar_verificacion(request):
    """
    Permite reenviar el correo de verificación si el usuario lo perdió.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = User.objects.get(email=email)

            if user.is_active:
                messages.info(request, 'Esa cuenta ya está verificada. Puedes iniciar sesión.')
                return redirect('login')

            enviar_correo_verificacion(request, user)
            messages.success(request, f'Reenviamos el correo a {email}. Revisa tu bandeja.')
            return redirect('login')

        except User.DoesNotExist:
            messages.error(request, 'No existe ninguna cuenta con ese correo.')
            return redirect('reenviar_verificacion')

    return render(request, 'web/reenviar_verificacion.html')

# ═══════════════════════════════════════════
#         GESTIÓN DE CERTIFICADOS (DOCENTE)
# ═══════════════════════════════════════════

@login_required
def gestionar_certificados(request, clase_id):
    """
    Pantalla donde el docente selecciona a qué estudiantes emitir certificados.
    """
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')

    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)

    # Requisitos mínimos para certificar
    PROGRESO_MINIMO = 100
    PROMEDIO_MINIMO = 3.0

    estudiantes = clase.estudiantes.all()
    total_ejercicios = Ejercicio.objects.filter(clase=clase).count()

    data = []
    for estudiante in estudiantes:
        # Calcular progreso (ejercicios aprobados / total)
        completados = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio__clase=clase,
            aprobado=True
        ).values('ejercicio').distinct().count()

        progreso = round((completados / total_ejercicios) * 100) if total_ejercicios > 0 else 0

        # Calcular promedio
        promedio = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio__clase=clase,
            calificacion__isnull=False
        ).aggregate(avg=Avg('calificacion'))['avg'] or 0
        promedio = round(float(promedio), 1)

        # Verificar si ya tiene certificado
        certificado = Certificado.objects.filter(
            estudiante=estudiante,
            clase=clase,
            activo=True
        ).first()

        puede_certificar = (
            progreso >= PROGRESO_MINIMO
            and promedio >= PROMEDIO_MINIMO
            and certificado is None
        )

        data.append({
            'estudiante': estudiante,
            'progreso': progreso,
            'completados': completados,
            'total': total_ejercicios,
            'promedio': promedio,
            'certificado': certificado,
            'puede_certificar': puede_certificar,
        })

    # Ordenar: primero los que pueden certificar, luego por promedio
    data.sort(key=lambda x: (not x['puede_certificar'], -x['promedio']))

    context = {
        'clase': clase,
        'data': data,
        'total_elegibles': sum(1 for d in data if d['puede_certificar']),
        'total_emitidos': sum(1 for d in data if d['certificado']),
        'progreso_minimo': PROGRESO_MINIMO,
        'promedio_minimo': PROMEDIO_MINIMO,
    }

    return render(request, 'docente/gestionar_certificados.html', context)


@login_required
@require_POST
def emitir_certificados_lote(request, clase_id):
    """
    Emite certificados a los estudiantes seleccionados.
    """
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')

    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    estudiantes_ids = request.POST.getlist('estudiantes')

    if not estudiantes_ids:
        messages.warning(request, 'No seleccionaste ningún estudiante.')
        return redirect('gestionar_certificados', clase_id=clase.id)

    total_ejercicios = Ejercicio.objects.filter(clase=clase).count()
    PROGRESO_MINIMO = 100
    PROMEDIO_MINIMO = 3.0

    emitidos = 0
    omitidos = 0

    for estudiante_id in estudiantes_ids:
        estudiante = get_object_or_404(User, id=estudiante_id)

        # Validar
        if estudiante not in clase.estudiantes.all():
            continue

        completados = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio__clase=clase,
            aprobado=True
        ).values('ejercicio').distinct().count()

        progreso = round((completados / total_ejercicios) * 100) if total_ejercicios > 0 else 0

        promedio = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio__clase=clase,
            calificacion__isnull=False
        ).aggregate(avg=Avg('calificacion'))['avg'] or 0
        promedio = round(float(promedio), 1)

        if progreso < PROGRESO_MINIMO or promedio < PROMEDIO_MINIMO:
            omitidos += 1
            continue

        # Crear o reactivar certificado
        certificado, created = Certificado.objects.get_or_create(
            estudiante=estudiante,
            clase=clase,
            defaults={
                'docente': request.user,
                'promedio_final': promedio,
                'progreso_final': progreso,
                'horas_completadas': total_ejercicios * 2,
            }
        )

        if not created:
            certificado.activo = True
            certificado.promedio_final = promedio
            certificado.progreso_final = progreso
            certificado.save()

        emitidos += 1

        # Notificar al estudiante
        try:
            from notificaciones.services import crear_notificacion
            crear_notificacion(
                usuario=estudiante,
                tipo='sistema',
                titulo='🎓 ¡Nuevo certificado!',
                mensaje=f'Has recibido un certificado por completar la clase "{clase.nombre}".',
                url_destino='/certificados/'
            )
        except Exception:
            pass

    if emitidos > 0:
        messages.success(request, f'✅ {emitidos} certificado(s) emitido(s) correctamente.')
    if omitidos > 0:
        messages.warning(request, f'⚠️ {omitidos} estudiante(s) no cumplían los requisitos.')

    return redirect('gestionar_certificados', clase_id=clase.id)


@login_required
def revocar_certificado(request, certificado_id):
    """
    Revoca un certificado emitido (opcional pero útil).
    """
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')

    certificado = get_object_or_404(
        Certificado,
        id=certificado_id,
        docente=request.user
    )

    certificado.activo = False
    certificado.save(update_fields=['activo'])

    messages.info(
        request,
        f'Certificado de {certificado.estudiante.get_full_name() or certificado.estudiante.username} revocado.'
    )

    return redirect('gestionar_certificados', clase_id=certificado.clase.id)