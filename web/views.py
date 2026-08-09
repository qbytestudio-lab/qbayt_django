from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from web.models import Perfil
from django.contrib.auth.decorators import login_required, user_passes_test
from docente.models import Clase, SolicitudClase, Actividad, Pregunta, Opcion, RespuestaEstudiante
from .models import Curso, InscripcionCurso
from docente.utils import calcular_progreso_clase
from django.shortcuts import get_object_or_404
import json
from datetime import datetime, timedelta
from django.utils import timezone



def index(request):
    return render(request, 'web/index.html')

@login_required
def inicio(request):
    cursos_teoria = Curso.objects.filter(categoria='teoria')
    cursos_auditivo = Curso.objects.filter(categoria='auditivo')
    cursos_instrumento = Curso.objects.filter(categoria='instrumento')
    
    return render(request, 'web/inicio.html', {
        'cursos_teoria': cursos_teoria,
        'cursos_auditivo': cursos_auditivo,
        'cursos_instrumento': cursos_instrumento,
    })

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

    # Crear el usuario
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password1,
        first_name=first_name,
        last_name=last_name,
    )
    user.save()

    # Crear su perfil asociado
    Perfil.objects.create(user=user, rol=rol)

    # Iniciar sesión automáticamente de inmediato
    login(request, user)

    messages.success(request, '¡Cuenta creada con éxito!')

    # Si es estudiante, mandarlo a configurar su nivel musical; si es otro rol, a inicio
    if rol == 'estudiante':
      return redirect('login')
    else:
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
    clases = request.user.clases_estudiante.all()

    progreso_clases = []
    for clase in clases:
        progreso_clases.append({
            'clase': clase,
            'porcentaje': calcular_progreso_clase(request.user, clase)
        })

    progreso_general = round(sum(p['porcentaje'] for p in progreso_clases) / len(progreso_clases)) if progreso_clases else 0

    ejercicios_hechos = RespuestaEstudiante.objects.filter(
        estudiante=request.user
    ).values('actividad').distinct().count()

    total_actividades = Actividad.objects.filter(leccion__clase__in=clases).count()
    pendientes_count = total_actividades - ejercicios_hechos

    # Últimas actividades completadas con su puntaje
    respuestas = RespuestaEstudiante.objects.filter(
        estudiante=request.user
    ).select_related('actividad', 'actividad__leccion__clase', 'opcion').order_by('-fecha')

    actividades_vistas = {}
    for r in respuestas:
        act_id = r.actividad_id
        if act_id not in actividades_vistas:
            actividades_vistas[act_id] = {'correctas': 0, 'total': 0, 'actividad': r.actividad}
        actividades_vistas[act_id]['total'] += 1
        if r.opcion.es_correcta:
            actividades_vistas[act_id]['correctas'] += 1

    actividades_completadas = []
    for data in list(actividades_vistas.values())[:5]:
        puntaje = round((data['correctas'] / data['total']) * 100) if data['total'] > 0 else 0
        actividades_completadas.append({
            'titulo': data['actividad'].titulo,
            'clase_nombre': data['actividad'].leccion.clase.nombre,
            'puntaje': puntaje,
        })

    return render(request, 'web/progreso.html', {
        'clases': clases,
        'progreso_clases': progreso_clases,
        'progreso_general': progreso_general,
        'ejercicios_hechos': ejercicios_hechos,
        'pendientes_count': pendientes_count,
        'actividades_completadas': actividades_completadas,
    })

def certificados(request):
    return render(request, 'web/certificados.html')

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
    Vista del calendario - Versión simplificada
    """
    from django.utils import timezone
    import json
    
    usuario = request.user
    
    # Obtener inscripciones del estudiante
    inscripciones = InscripcionCurso.objects.filter(estudiante=usuario).select_related('curso')
    
    # Eventos para FullCalendar
    eventos = []
    
    # Agregar cursos como eventos
    for insc in inscripciones:
        fecha = insc.curso.fecha_creacion.date() if insc.curso.fecha_creacion else timezone.now().date()
        eventos.append({
            'title': f'📚 {insc.curso.nombre}',
            'start': fecha.isoformat(),
            'tipo': 'clase',
            'url': f'/cursos/detalle/{insc.curso.id}/',
            'descripcion': f'Clase: {insc.curso.nombre}'
        })
    
    # Eventos del día de hoy
    hoy = timezone.now().date()
    eventos_hoy = [e for e in eventos if e['start'] == hoy.isoformat()]
    
    # Próximas entregas (vacío por ahora)
    proximos = []
    
    # Convertir a JSON
    eventos_json = json.dumps(eventos, default=str)
    
    # Contar correctamente
    total_clases = inscripciones.count()
    
    context = {
        'eventos_json': eventos_json,
        'eventos_hoy': eventos_hoy,
        'proximos': proximos,
        'total_clases': total_clases,
        'actividades_pendientes': 0,
        'actividades_completadas': 0,
        'hoy': hoy,
        'clases': inscripciones,  # ✅ AGREGADO: Para compatibilidad
    }
    
    return render(request, 'web/calendario.html', context)