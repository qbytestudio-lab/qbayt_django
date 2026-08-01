from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ejercicios.models import Ejercicio, Pregunta, Opcion, IntentoEjercicio, RespuestaEstudiante
from docente.utils import calcular_progreso_clase
from clase.models import Clase
from docente.models import SolicitudClase, Actividad

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
    
        # 🛠️ CORREGIDO: Usando 'intento__estudiante' y contando los ejercicios únicos a través del intento
        ejercicios_hechos = RespuestaEstudiante.objects.filter(
        intento__estudiante=request.user
    ).values('intento__ejercicio').distinct().count()

    return render(request, 'estudiante/perfil_estudiante.html', {
        'clases': clases,
        'solicitudes': solicitudes,
        'progreso_clases': progreso_clases,
        'progreso_general': progreso_general,
        'ejercicios_hechos': ejercicios_hechos,
        'total_actividades': total_actividades,
    })
@login_required
def configurar_nivel_view(request):
  usuario = request.user

  if request.method == 'POST':
    nuevo_nivel = request.POST.get('nivel_musical')
    if nuevo_nivel in ['1', '2', '3', '4']:
      usuario.nivel_musical = int(nuevo_nivel)
      usuario.save()
      # Redirige a su panel principal o perfil una vez configurado
      return redirect('estudiante:mis_clases')  # O la ruta que prefieras

  return render(request, 'estudiante/configurar_nivel.html', {'usuario': usuario})

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

    # Adjuntamos el intento exclusivo del usuario actual a cada ejercicio
    for ejercicio in ejercicios:
        ejercicio.mi_intento = ejercicio.intentos.filter(estudiante=request.user).first()

    return render(request, 'estudiante/detalle_clase_estudiante.html', {
        'clase': clase,
        'ejercicios': ejercicios,
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
def responder_actividad(request, pregunta_id): # Nota: 'pregunta_id' aquí suele ser el id del Ejercicio
    ejercicio = get_object_or_404(Ejercicio, id=pregunta_id)
    clase = ejercicio.clase

    # Verificar si ya tiene un intento activo o enviado para no duplicar
    intento_existente = IntentoEjercicio.objects.filter(estudiante=request.user, ejercicio=ejercicio).first()

    if request.method == 'POST':
        # 1. Creamos o recuperamos el intento del estudiante para este ejercicio
        intento, created = IntentoEjercicio.objects.get_or_create(
            estudiante=request.user,
            ejercicio=ejercicio
        )

        # Limpiamos respuestas anteriores por si acaso se está reenviando
        intento.respuestas.all().delete()

        # 2. Recorremos las preguntas del ejercicio para capturar lo que respondió
        preguntas = ejercicio.preguntas.all()
        for pregunta in preguntas:
            # Obtenemos el ID de la opción seleccionada en el formulario HTML (ej: name="pregunta_5")
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            
            if opcion_id:
                opcion_seleccionada = get_object_or_404(Opcion, id=opcion_id)
                
                # Guardamos la respuesta del estudiante
                RespuestaEstudiante.objects.create(
                    intento=intento,
                    pregunta=pregunta,
                    opcion_seleccionada=opcion_seleccionada
                )

        messages.success(request, "¡Ejercicio enviado con éxito! Quedó pendiente de calificación.")
        
        # Redirigimos a la vista de la clase del estudiante
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

    return render(request, 'estudiante/responder_actividad.html', {
        'actividad': ejercicio,
        'clase': clase,
        'preguntas': ejercicio.preguntas.all().prefetch_related('opciones'),
    })