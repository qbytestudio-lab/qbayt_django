from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from docente.models import Clase, SolicitudClase, Actividad, Pregunta, Opcion, RespuestaEstudiante
from docente.utils import calcular_progreso_clase

def calcular_progreso_clase(estudiante, clase):
    """Devuelve el % de actividades completadas en una clase."""
    total_actividades = Actividad.objects.filter(leccion__clase=clase).count()
    if total_actividades == 0:
        return 0
    completadas = RespuestaEstudiante.objects.filter(
        estudiante=estudiante,
        actividad__leccion__clase=clase
    ).values('actividad').distinct().count()
    return round((completadas / total_actividades) * 100)


@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clases = request.user.clases_estudiante.all()
    solicitudes = SolicitudClase.objects.filter(estudiante=request.user)

    # Progreso por cada clase
    progreso_clases = []
    for clase in clases:
        progreso_clases.append({
            'clase': clase,
            'porcentaje': calcular_progreso_clase(request.user, clase)
        })

    # Progreso general (promedio de todas las clases)
    if progreso_clases:
        progreso_general = round(sum(p['porcentaje'] for p in progreso_clases) / len(progreso_clases))
    else:
        progreso_general = 0

    # Totales reales
    total_actividades = Actividad.objects.filter(leccion__clase__in=clases).count()
    ejercicios_hechos = RespuestaEstudiante.objects.filter(
        estudiante=request.user
    ).values('actividad').distinct().count()

    return render(request, 'estudiante/perfil_estudiante.html', {
        'clases': clases,
        'solicitudes': solicitudes,
        'progreso_clases': progreso_clases,
        'progreso_general': progreso_general,
        'ejercicios_hechos': ejercicios_hechos,
        'total_actividades': total_actividades,
    })

@login_required
def unirse_clase(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()

        try:
            clase = Clase.objects.get(codigo=codigo)

            if request.user in clase.estudiantes.all():
                messages.warning(request, 'Ya estás en esta clase.')
            else:
                clase.estudiantes.add(request.user)
                messages.success(request, f'¡Te uniste a "{clase.nombre}"!')

            # Solo redirige si la clase existe
            return redirect('detalle_clase_estudiante', clase_id=clase.id)

        except Clase.DoesNotExist:
            messages.error(request, 'Código inválido.')
            return redirect('explorar_clases')  # o la página donde está el formulario

    return redirect('explorar_clases')

@login_required
def solicitar_clase(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    if request.method == 'POST':
        clase_id = request.POST.get('clase_id')
        clase = get_object_or_404(Clase, id=clase_id)
        if request.user in clase.estudiantes.all():
            messages.warning(request, 'Ya estás en esta clase.')
        elif SolicitudClase.objects.filter(clase=clase, estudiante=request.user, estado='pendiente').exists():
            messages.warning(request, 'Ya tienes una solicitud pendiente para esta clase.')
        else:
            SolicitudClase.objects.create(clase=clase, estudiante=request.user)
            messages.success(request, f'Solicitud enviada a "{clase.nombre}". Espera que el docente la acepte.')
    return redirect('perfil_estudiante')

@login_required
def salir_clase(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id)
    clase.estudiantes.remove(request.user)
    messages.success(request, f'Saliste de "{clase.nombre}".')
    return redirect('perfil_estudiante')

@login_required
def explorar_clases(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clases = Clase.objects.exclude(estudiantes=request.user)
    solicitudes_enviadas = SolicitudClase.objects.filter(
        estudiante=request.user
    ).values_list('clase_id', flat=True)
    return render(request, 'estudiante/explorar_clases.html', {
        'clases': clases,
        'solicitudes_enviadas': solicitudes_enviadas,
    })

@login_required
def detalle_clase_estudiante(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, estudiantes=request.user)
      # IDs de actividades ya completadas por el estudiante
    completadas = RespuestaEstudiante.objects.filter(
        estudiante=request.user,
        actividad__leccion__clase=clase
    ).values_list('actividad_id', flat=True).distinct()

    return render(request, 'estudiante/detalle_clase_estudiante.html', {
        'clase': clase,
        'completadas': list(completadas),
    })

@login_required
def detalle_actividad_estudiante(request, actividad_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    actividad = get_object_or_404(Actividad, id=actividad_id)
    clase = actividad.leccion.clase

    # Verificar que el estudiante está en la clase
    if request.user not in clase.estudiantes.all():
        return redirect('inicio')

    ya_respondio = RespuestaEstudiante.objects.filter(
        estudiante=request.user, actividad=actividad
    ).exists()

    revision = []
    correctas = incorrectas = total = puntaje = 0

    if ya_respondio:
        respuestas = RespuestaEstudiante.objects.filter(
            estudiante=request.user, actividad=actividad
        ).select_related('pregunta', 'opcion')
        total = respuestas.count()
        for resp in respuestas:
            es_correcta = resp.opcion.es_correcta
            if es_correcta:
                correctas += 1
            else:
                incorrectas += 1
            revision.append({
                'pregunta': resp.pregunta,
                'respuesta': resp.opcion,
                'es_correcta': es_correcta,
            })
        puntaje = round((correctas / total) * 100) if total > 0 else 0

    return render(request, 'detalle_actividad_estudiante.html', {
        'actividad': actividad,
        'clase': clase,
        'ya_respondio': ya_respondio,
        'revision': revision,
        'correctas': correctas,
        'incorrectas': incorrectas,
        'total': total,
        'puntaje': puntaje,
    })


@login_required
def responder_actividad(request, actividad_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    actividad = get_object_or_404(Actividad, id=actividad_id)
    clase = actividad.leccion.clase

    if request.user not in clase.estudiantes.all():
        return redirect('inicio')

    if request.method == 'POST':
        preguntas = actividad.preguntas.all()
        for pregunta in preguntas:
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                opcion = get_object_or_404(Opcion, id=opcion_id, pregunta=pregunta)
                RespuestaEstudiante.objects.get_or_create(
                    estudiante=request.user,
                    actividad=actividad,
                    pregunta=pregunta,
                    defaults={'opcion': opcion}
                )
        messages.success(request, '¡Respuestas enviadas!')

    return redirect('detalle_actividad_estudiante', actividad_id=actividad_id)