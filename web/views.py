from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from web.models import Perfil
from django.contrib.auth.decorators import login_required
from docente.models import Clase, SolicitudClase, Actividad, Pregunta, Opcion, RespuestaEstudiante
from .models import Curso, InscripcionCurso
from docente.utils import calcular_progreso_clase

@login_required
def mis_clases(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
        
    clases_inscritas = Clase.objects.filter(estudiantes=request.user)
    
    # 🛠️ CORRECCIÓN DE LA RUTA AQUÍ:
    return render(request, 'web/mis_clases.html', {
        'clases': clases_inscritas
    })

def index(request):
    return render(request, 'web/index.html')

@login_required
def inicio(request):
    return render(request, 'web/inicio.html')

@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    return render(request, 'perfil_estudiante.html')

@login_required
def perfil_docente(request):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    return render(request, 'perfil_docente.html')

@login_required
def perfil_administrador(request):
    if request.user.perfil.rol != 'administrador':
        return redirect('inicio')
    return render(request, 'perfil_admin.html')

def registro(request):
    if request.method == 'POST':
        first_name = request.POST ['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        rol = request.POST['rol']

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('registro')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El usuario ya existe.')
            return redirect('registro')

        user = User.objects.create_user(username=username, email=email, password=password1, first_name=first_name,
    last_name=last_name)
        user.save()
        Perfil.objects.create(user=user, rol=rol)
        messages.success(request, '¡Cuenta creada! Inicia sesión.')
        return redirect('login')

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
    if request.user.perfil.rol == 'estudiante':
        inscripciones = InscripcionCurso.objects.filter(estudiante=request.user).select_related('curso')
        cursos_inscritos_ids = inscripciones.values_list('curso_id', flat=True)
        catalogo = Curso.objects.exclude(id__in=cursos_inscritos_ids)
        return render(request, 'clase/cursos.html', {
            'inscripciones': inscripciones,
            'catalogo': catalogo,
        })
    return render(request, 'clase/cursos.html', {})


@login_required
def agregar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    InscripcionCurso.objects.get_or_create(estudiante=request.user, curso=curso)
    messages.success(request, f'Te uniste a "{curso.nombre}".')
    return redirect('cursos')


@login_required
def eliminar_curso(request, curso_id):
    InscripcionCurso.objects.filter(estudiante=request.user, curso_id=curso_id).delete()
    messages.success(request, 'Dejaste de seguir el curso.')
    return redirect('cursos')


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