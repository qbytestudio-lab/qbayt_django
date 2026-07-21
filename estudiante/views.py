from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ejercicios.models import Ejercicio, Pregunta, Opcion 
from docente.utils import calcular_progreso_clase
from clase.models import Clase
from docente.models import SolicitudClase, Actividad, RespuestaEstudiante

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

            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

        except Clase.DoesNotExist:
            messages.error(request, 'Código inválido.')
            return redirect('estudiante:explorar_clases')

    return redirect('estudiante:explorar_clases')

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
    return redirect('estudiante:perfil_estudiante')

@login_required
def salir_clase(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id)
    clase.estudiantes.remove(request.user)
    messages.success(request, f'Saliste de "{clase.nombre}".')
    return redirect('estudiante:perfil_estudiante')

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
    ejercicios = clase.ejercicios.all()
      # IDs de actividades ya completadas por el estudiante
    completadas = RespuestaEstudiante.objects.filter(
        estudiante=request.user,
        actividad__leccion__clase=clase
    ).values_list('actividad_id', flat=True).distinct()

    return render(request, 'estudiante/detalle_clase_estudiante.html', {
        'clase': clase,
        'completadas': list(completadas),
        'ejercicios' : ejercicios,
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
def responder_actividad(request, pregunta_id): # <-- Cambiamos el nombre aquí
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    
    # 1. Buscamos el EJERCICIO, no la ACTIVIDAD
    ejercicio = get_object_or_404(Ejercicio, id=pregunta_id)
    clase = ejercicio.clase # Ajustado según tu models.py

    if request.user not in clase.estudiantes.all():
        return redirect('inicio')

    # 2. Ajustamos la lógica de 'ya_respondio' para el EJERCICIO
    ya_respondio = RespuestaEstudiante.objects.filter(
        estudiante=request.user, ejercicio=ejercicio 
    ).exists()
    
    if ya_respondio:
        return redirect('detalle_actividad_estudiante', actividad_id=ejercicio.id)

    if request.method == 'POST':
        preguntas = ejercicio.preguntas.all()
        for pregunta in preguntas:
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                opcion = get_object_or_404(Opcion, id=opcion_id, pregunta=pregunta)
                RespuestaEstudiante.objects.get_or_create(
                    estudiante=request.user,
                    ejercicio=ejercicio, # Ajustado
                    pregunta=pregunta,
                    defaults={'opcion': opcion}
                )
        messages.success(request, '¡Respuestas enviadas!')
        return redirect('detalle_actividad_estudiante', actividad_id=ejercicio.id)

    # 3. Si es GET, renderizamos el formulario
    preguntas = ejercicio.preguntas.all().prefetch_related('opciones')
    return render(request, 'estudiante/responder_actividad.html', {
        'actividad': ejercicio, # Mantenemos el nombre 'actividad' en el template para no tener que cambiar todo el HTML
        'clase': clase,
        'preguntas': preguntas,
    })