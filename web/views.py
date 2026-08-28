from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from web.models import Perfil
from django.contrib.auth.decorators import login_required, user_passes_test
from docente.models import Clase, SolicitudClase, Actividad, Pregunta, Opcion, RespuestaEstudiante
from .models import Curso, InscripcionCurso, Modulo
from docente.utils import calcular_progreso_clase
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
        rol = request.POST.get('rol', 'estudiante')  # Por defecto estudiante

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('registro')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El usuario ya existe.')
            return redirect('registro')

        # Creamos el usuario de una vez sin pasar por sesiones temporales
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
        )
        
        # Creamos su perfil con el rol correspondiente
        Perfil.objects.create(user=user, rol=rol)
        
        # Iniciamos sesión automáticamente y mandamos éxito
        login(request, user)
        messages.success(request, '¡Cuenta creada con éxito!')
        return redirect('inicio')

    return render(request, 'web/registro.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('inicio')
        else:
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
def cursos(request):
    # Verificar si el usuario es docente
    es_docente = request.user.perfil.rol == 'docente'
    es_estudiante = request.user.perfil.rol == 'estudiante'
    
    # Obtener inscripciones del usuario
    inscripciones = InscripcionCurso.objects.filter(
        estudiante=request.user
    ).select_related('curso').order_by('-fecha_inscripcion')
    
    # IDs de cursos a los que está inscrito
    cursos_inscritos_ids = inscripciones.values_list('curso_id', flat=True)
    inscrito_ids = [str(id) for id in cursos_inscritos_ids]
    
    # Obtener cursos creados por el usuario (si es docente)
    cursos_creados = []
    if es_docente or request.user.is_superuser:
        cursos_creados = Curso.objects.filter(creado_por=request.user).order_by('-fecha_creacion')
    
    # Catálogo: todos los cursos disponibles
    catalogo = Curso.objects.all().order_by('nombre')
    
    # Para estudiantes: ocultar cursos ya inscritos
    if es_estudiante:
        catalogo = Curso.objects.exclude(id__in=cursos_inscritos_ids).order_by('nombre')
    
    context = {
        'inscripciones': inscripciones,
        'catalogo': catalogo,
        'inscrito_ids': inscrito_ids,
        'cursos_creados': cursos_creados,  # ✅ PASAMOS los cursos creados
        'es_docente': es_docente,
        'es_estudiante': es_estudiante,
    }
    
    return render(request, 'clase/cursos.html', context)


@login_required
def agregar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    InscripcionCurso.objects.get_or_create(estudiante=request.user, curso=curso)
    messages.success(request, f'Te uniste a "{curso.nombre}".')
    return redirect('cursos')


@login_required
def crear_curso(request):
    # SOLO AGREGAMOS: verificación de permisos
    if request.user.perfil.rol != 'docente' and not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para crear cursos')
        return redirect('cursos')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        categoria = request.POST.get('categoria')
        nivel = request.POST.get('nivel', 'basico')  #  NUEVO: campo adicional
        duracion_horas = request.POST.get('duracion_horas', 0)  #  NUEVO
        imagen_url = request.POST.get('imagen_url')  #  NUEVO
        icono = request.POST.get('icono', 'bi-book')  #  NUEVO

        # CREAMOS el curso con todos los campos
        curso = Curso.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            categoria=categoria,
            nivel=nivel,
            duracion_horas=duracion_horas or 0,
            imagen_url=imagen_url,
            icono=icono,
            creado_por=request.user  # NUEVO: quién lo creó
        )
        
        # Procesar imagen si se subió
        if request.FILES.get('imagen'):
            curso.imagen = request.FILES['imagen']
            curso.save()

        messages.success(request, "Curso creado correctamente.")
        return redirect('cursos')

    return redirect('cursos')

@login_required
def eliminar_curso(request, curso_id):
    InscripcionCurso.objects.filter(estudiante=request.user, curso_id=curso_id).delete()
    messages.success(request, 'Dejaste de seguir el curso.')
    return redirect('cursos')

@login_required
def eliminar_curso_propio(request, curso_id):
    """
    Eliminar un curso creado por el docente
    Solo el docente que lo creó o un admin puede eliminarlo
    """
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar permisos
    if request.user.perfil.rol == 'docente' or request.user.is_superuser:
        # Verificar que el docente sea el creador o sea admin
        if curso.creado_por == request.user or request.user.is_superuser:
            nombre_curso = curso.nombre
            curso.delete()
            messages.success(request, f'El curso "{nombre_curso}" fue eliminado correctamente.')
        else:
            messages.error(request, 'No tienes permiso para eliminar este curso.')
    else:
        messages.error(request, 'Solo los docentes pueden eliminar cursos.')
    
    return redirect('cursos')

@login_required
def detalle_curso(request, curso_id):
    """
    Vista de detalle del curso - Para ver contenido y gestionar
    """
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar si el usuario está inscrito
    esta_inscrito = InscripcionCurso.objects.filter(
        estudiante=request.user, 
        curso=curso
    ).exists()
    
    # Verificar si el usuario es el creador (docente)
    es_creador = curso.creado_por == request.user
    
    # Obtener inscripciones (estudiantes inscritos)
    inscripciones = InscripcionCurso.objects.filter(curso=curso).select_related('estudiante')
    
    # Obtener progreso del usuario si está inscrito
    progreso_usuario = 0
    if esta_inscrito:
        insc = InscripcionCurso.objects.get(estudiante=request.user, curso=curso)
        progreso_usuario = insc.progreso
    
    context = {
        'curso': curso,
        'esta_inscrito': esta_inscrito,
        'es_creador': es_creador,
        'inscripciones': inscripciones,
        'progreso_usuario': progreso_usuario,
        'total_estudiantes': inscripciones.count(),
    }
    
    return render(request, 'clase/detalle_curso.html', context)



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
    Vista de certificados del estudiante
    """
    
    # Obtener clases donde el estudiante está inscrito
    clases_inscritas = request.user.clases_estudiante.all()
    
    certificados_lista = []
    
    for clase in clases_inscritas:
        # Calcular progreso
        total_ejercicios = Ejercicio.objects.filter(clase=clase).count()
        ejercicios_completados = IntentoEjercicio.objects.filter(
            estudiante=request.user,
            ejercicio__clase=clase,
            aprobado=True
        ).values('ejercicio').distinct().count()
        
        progreso = round((ejercicios_completados / total_ejercicios) * 100) if total_ejercicios > 0 else 0
        
        # Solo mostrar certificado si el progreso es 100%
        if progreso >= 100:
            # Obtener promedio
            promedio = IntentoEjercicio.objects.filter(
                estudiante=request.user,
                ejercicio__clase=clase,
                calificacion__isnull=False
            ).aggregate(avg=Avg('calificacion'))['avg'] or 0
            
            # Obtener fecha de completación
            ultimo_intento = IntentoEjercicio.objects.filter(
                estudiante=request.user,
                ejercicio__clase=clase,
                aprobado=True
            ).order_by('-fecha_envio').first()
            
            # Generar código de verificación único
            codigo_verificacion = f"CERT-{timezone.now().year}-{clase.id:04d}-{request.user.id:04d}"
            
            # Calcular horas (estimación: 2 horas por ejercicio)
            horas_completadas = total_ejercicios * 2
            
            certificados_lista.append({
                'id': clase.id,
                'nombre_curso': clase.nombre,
                'instructor': clase.docente.get_full_name() or clase.docente.username,
                'fecha_emision': ultimo_intento.fecha_envio.strftime("%d de %B, %Y") if ultimo_intento else timezone.now().strftime("%d de %B, %Y"),
                'codigo_verificacion': codigo_verificacion,
                'horas': horas_completadas,
                'promedio': round(promedio, 1),
                'progreso': progreso,
            })
    
    # Ordenar por fecha (más recientes primero)
    certificados_lista.sort(key=lambda x: x['fecha_emision'], reverse=True)
    
    context = {
        'certificados': certificados_lista,
        'total_certificados': len(certificados_lista),
    }
    
    return render(request, 'web/certificados.html', context)
@login_required
def mis_clases(request):
    if request.user.perfil.rol == 'docente':
        clases = Clase.objects.filter(docente=request.user)
        solicitudes_pendientes = SolicitudClase.objects.filter(
            clase__docente=request.user, estado='pendiente'
        )
        total_estudiantes = sum(c.estudiantes.count() for c in clases)
        return render(request, 'web/mis_clases_docente.html', {
            'clases': clases,
            'solicitudes_pendientes': solicitudes_pendientes,
            'total_estudiantes': total_estudiantes,
        })
    else:
        clases = request.user.clases_estudiante.all()
        return render(request, 'web/mis_clases.html', {'clases': clases})

@login_required
def calendario(request):
    """
    Vista del calendario - Versión corregida
    """
    
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
        # Verificar si el estudiante tiene intentos aprobados
        intento_aprobado = IntentoEjercicio.objects.filter(
            estudiante=usuario,
            ejercicio=ejercicio,
            aprobado=True
        ).exists()
        
        if intento_aprobado:
            # Ejercicio completado y aprobado
            actividades_completadas_count += 1
        else:
            # Ejercicio pendiente
            actividades_pendientes_count += 1
            
            # Agregar a próximos si tiene fecha límite futura
            if ejercicio.fecha_limite and ejercicio.fecha_limite >= timezone.now():
                proximos.append(ejercicio)
            
            # Agregar al calendario si tiene fecha límite
            if ejercicio.fecha_limite:
                eventos.append({
                    'title': f'✏️ {ejercicio.titulo}',
                    'start': ejercicio.fecha_limite.isoformat(),
                    'tipo': 'actividad',
                    'url': f'/estudiante/clase/{ejercicio.clase.id}/',
                })
    
    # Ordenar próximos por fecha límite
    if proximos:
        proximos.sort(key=lambda x: x.fecha_limite if x.fecha_limite else timezone.now())
    
    hoy = timezone.now()
    
    # Convertir a JSON
    eventos_json = json.dumps(eventos, default=str)
    
    # Eventos del día de hoy
    eventos_hoy = [e for e in eventos if e['start'] == hoy.date().isoformat()]
    
    context = {
        'eventos_json': eventos_json,
        'eventos_hoy': eventos_hoy,
        'proximos': proximos,
        'total_clases': clases_inscritas.count(),
        'actividades_pendientes': actividades_pendientes_count,
        'actividades_completadas': actividades_completadas_count,
        'hoy': hoy.date(),
        'clases': clases_inscritas,
    }
    
    return render(request, 'web/calendario.html', context)
@login_required
def continuar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    
    # ✅ Cambia 'orden' por 'id' (o quita el order_by si no tienes campo de orden)
    modulos = curso.modulos.all().order_by('id')
    
    # Obtener módulo actual (por parámetro o el primero)
    modulo_id = request.GET.get('modulo')
    if modulo_id:
        modulo_actual = get_object_or_404(Modulo, id=modulo_id, curso=curso)
    else:
        modulo_actual = modulos.first()
    
    # Módulos completados (simulado - deberías guardarlo en BD)
    modulos_completados = request.session.get(f'completados_{curso_id}', [])
    
    # Calcular progreso
    total_modulos = modulos.count()
    completados_count = len(modulos_completados)
    progreso_total = int((completados_count / total_modulos) * 100) if total_modulos > 0 else 0
    
    # Módulos anterior y siguiente
    modulo_anterior = None
    modulo_siguiente = None
    
    if modulo_actual:
        modulos_list = list(modulos)
        # ✅ Usa index() para encontrar la posición
        try:
            current_index = modulos_list.index(modulo_actual)
            
            if current_index > 0:
                modulo_anterior = modulos_list[current_index - 1]
            if current_index < len(modulos_list) - 1:
                modulo_siguiente = modulos_list[current_index + 1]
        except ValueError:
            pass
    
    context = {
        'curso': curso,
        'modulos': modulos,
        'modulo_actual': modulo_actual,
        'modulo_anterior': modulo_anterior,
        'modulo_siguiente': modulo_siguiente,
        'modulos_completados': modulos_completados,
        'progreso_total': progreso_total,
    }
    
    return render(request, 'clase/continuar_curso.html', context)

@login_required
def explorar_clases(request):
    """
    Vista unificada para explorar clases disponibles
    """
    from docente.models import SolicitudClase
    
    usuario = request.user
    
    # Clases donde el usuario NO está inscrito y NO es docente
    clases = Clase.objects.exclude(
        estudiantes=usuario
    ).exclude(
        docente=usuario
    )
    
    # Filtros
    categoria = request.GET.get('categoria')
    if categoria:
        clases = clases.filter(categoria_tema=categoria)
    
    # Búsqueda
    query = request.GET.get('q')
    if query:
        from django.db.models import Q
        clases = clases.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query)
        )
    
    # SOLO solicitudes PENDIENTES
    solicitudes_enviadas = SolicitudClase.objects.filter(
        estudiante=usuario,
        estado='pendiente'
    ).values_list('clase_id', flat=True)
    
    # Solicitudes RECHAZADAS (para mostrar botón re-solicitar)
    solicitudes_rechazadas = SolicitudClase.objects.filter(
        estudiante=usuario,
        estado='rechazada'
    ).values_list('clase_id', flat=True)
    
    context = {
        'clases': clases,
        'categorias': Clase.TEMA_CATEGORIAS,
        'total_clases': clases.count(),
        'solicitudes_enviadas': solicitudes_enviadas,
        'solicitudes_rechazadas': solicitudes_rechazadas,
    }
    
    return render(request, 'estudiante/explorar_clases.html', context)

@login_required
def redirigir_curso_a_clase(request, curso_id):
    """
    Redirige URLs antiguas de cursos a la clase correspondiente
    """
    from clase.models import Clase
    
    # Intentar encontrar la clase con ese ID
    clase = Clase.objects.filter(id=curso_id).first()
    
    if clase:
        # Usar la URL correcta del estudiante
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)
    
    # Si no hay clase, redirigir a explorar
    return redirect('estudiante:explorar_clases')

@login_required
def descargar_certificado(request, clase_id):
    """
    Vista para descargar certificado en PDF
    """
    
    # Obtener la clase
    clase = get_object_or_404(Clase, id=clase_id)
    
    # Verificar que el estudiante esté inscrito
    if request.user not in clase.estudiantes.all():
        messages.error(request, 'No tienes acceso a este certificado.')
        return redirect('certificados')
    
    # Calcular datos del certificado
    total_ejercicios = Ejercicio.objects.filter(clase=clase).count()
    ejercicios_completados = IntentoEjercicio.objects.filter(
        estudiante=request.user,
        ejercicio__clase=clase,
        aprobado=True
    ).values('ejercicio').distinct().count()
    
    progreso = round((ejercicios_completados / total_ejercicios) * 100) if total_ejercicios > 0 else 0
    
    # Verificar que el progreso sea 100%
    if progreso < 100:
        messages.error(request, 'Aún no has completado esta clase al 100%.')
        return redirect('certificados')
    
    # Obtener promedio
    promedio = IntentoEjercicio.objects.filter(
        estudiante=request.user,
        ejercicio__clase=clase,
        calificacion__isnull=False
    ).aggregate(avg=Avg('calificacion'))['avg'] or 0
    
    # Obtener fecha de completación
    ultimo_intento = IntentoEjercicio.objects.filter(
        estudiante=request.user,
        ejercicio__clase=clase,
        aprobado=True
    ).order_by('-fecha_envio').first()
    
    fecha_emision = ultimo_intento.fecha_envio if ultimo_intento else timezone.now()
    
    # Intentar importar reportlab
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.colors import HexColor
        
        # Crear PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificado_{clase.nombre}.pdf"'
        
        # Crear canvas en orientación horizontal
        p = canvas.Canvas(response, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        # Colores
        color_principal = HexColor('#1db954')
        color_secundario = HexColor('#7c6fff')
        color_texto = HexColor('#333333')
        color_dorado = HexColor('#FFD700')
        
        # Fondo
        p.setFillColor(HexColor('#f8f9fe'))
        p.rect(0, 0, width, height, fill=1, stroke=0)
        
        # Borde decorativo
        p.setStrokeColor(color_dorado)
        p.setLineWidth(3)
        p.rect(30, 30, width-60, height-60, fill=0, stroke=1)
        
        # Borde interior
        p.setStrokeColor(color_principal)
        p.setLineWidth(1)
        p.rect(40, 40, width-80, height-80, fill=0, stroke=1)
        
        # Título principal
        p.setFillColor(color_principal)
        p.setFont("Helvetica-Bold", 28)
        p.drawCentredString(width/2, height-120, "CERTIFICADO")
        
        # Subtítulo
        p.setFillColor(color_secundario)
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width/2, height-150, "DE FINALIZACIÓN")
        
        # Línea decorativa
        p.setStrokeColor(color_dorado)
        p.setLineWidth(1.5)
        p.line(width/2 - 100, height-165, width/2 + 100, height-165)
        
        # Texto de presentación
        p.setFillColor(color_texto)
        p.setFont("Helvetica", 14)
        p.drawCentredString(width/2, height-200, "Este certificado se otorga a:")
        
        # Nombre del estudiante
        p.setFillColor(color_secundario)
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width/2, height-240, request.user.get_full_name() or request.user.username)
        
        # Texto de clase
        p.setFillColor(color_texto)
        p.setFont("Helvetica", 14)
        p.drawCentredString(width/2, height-280, "Por completar exitosamente la clase:")
        
        # Nombre de la clase
        p.setFillColor(color_principal)
        p.setFont("Helvetica-Bold", 20)
        p.drawCentredString(width/2, height-315, clase.nombre)
        
        # Detalles
        p.setFillColor(color_texto)
        p.setFont("Helvetica", 12)
        p.drawCentredString(width/2, height-360, f"Docente: {clase.docente.get_full_name() or clase.docente.username}")
        p.drawCentredString(width/2, height-380, f"Fecha: {fecha_emision.strftime('%d de %B de %Y')}")
        p.drawCentredString(width/2, height-400, f"Promedio: {promedio:.1f}")
        
        # Firma decorativa
        p.setStrokeColor(color_texto)
        p.setLineWidth(0.5)
        p.line(width/2 - 150, 120, width/2 + 150, 120)
        p.setFillColor(color_texto)
        p.setFont("Helvetica", 10)
        p.drawCentredString(width/2, 105, "Director de QBYT")
        
        # Sello decorativo
        p.setFillColor(color_dorado)
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(width/2, 200, "★ QBYT ★")
        
        p.showPage()
        p.save()
        
        return response
        
    except ImportError:
        # Si reportlab no está instalado, generar HTML simple
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Certificado - {clase.nombre}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: #f8f9fe;
                }}
                .certificado {{
                    border: 3px solid #FFD700;
                    padding: 50px;
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #1db954;
                    font-size: 36px;
                    margin-bottom: 10px;
                }}
                h2 {{
                    color: #7c6fff;
                    font-size: 24px;
                    margin-bottom: 30px;
                }}
                .nombre {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #333;
                    margin: 20px 0;
                }}
                .clase {{
                    font-size: 22px;
                    color: #1db954;
                    margin: 20px 0;
                }}
                .fecha {{
                    color: #666;
                    margin-top: 30px;
                }}
                .sello {{
                    display: inline-block;
                    width: 100px;
                    height: 100px;
                    border: 3px solid #FFD700;
                    border-radius: 50%;
                    line-height: 100px;
                    font-size: 12px;
                    color: #FFD700;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="certificado">
                <h1>CERTIFICADO</h1>
                <h2>DE FINALIZACIÓN</h2>
                <p>Se otorga a:</p>
                <div class="nombre">{request.user.get_full_name() or request.user.username}</div>
                <p>Por completar exitosamente la clase:</p>
                <div class="clase">{clase.nombre}</div>
                <p>Docente: {clase.docente.get_full_name() or clase.docente.username}</p>
                <p>Promedio: {promedio:.1f}</p>
                <p class="fecha">Fecha: {fecha_emision.strftime('%d de %B de %Y')}</p>
                <div class="sello">★ QBYT ★</div>
            </div>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="certificado_{clase.nombre}.html"'
        
        return response