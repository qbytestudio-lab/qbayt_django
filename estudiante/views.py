from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ejercicios.models import Ejercicio, Pregunta, Opcion, IntentoEjercicio, RespuestaEstudiante
from docente.utils import calcular_progreso_clase
from clase.models import Clase, InscripcionNivel
from docente.models import SolicitudClase, Actividad
from django.contrib.auth.models import User
from web.models import Perfil
from django.contrib.auth import login

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
    ejercicios_hechos = RespuestaEstudiante.objects.filter(intento__estudiante=request.user).values('intento__ejercicio').distinct().count()

    return render(request, 'estudiante/perfil_estudiante.html', {
        'clases': clases,
        'solicitudes': solicitudes,
        'progreso_clases': progreso_clases,
        'progreso_general': progreso_general,
        'ejercicios_hechos': ejercicios_hechos,
        'total_actividades': total_actividades,
    })

def configurar_nivel(request):
    if 'registro_temporal' not in request.session:
        return redirect('registro')

    datos = request.session['registro_temporal']

    if request.method == 'POST':
        nivel_seleccionado = request.POST.get('nivel') # Aquí captura el '1', '2', '3' o '4'

        # 1. Creamos el usuario
        user = User.objects.create_user(
            username=datos['username'],
            email=datos['email'],
            password=datos['password'],
            first_name=datos['first_name'],
            last_name=datos['last_name'],
        )
        user.save()

        # 2. Creamos su perfil
        Perfil.objects.create(user=user, rol=datos['rol'])

        # 3. ¡ESTO ES LO QUE FALTABA! Guardamos el nivel seleccionado en la app clase
        InscripcionNivel.objects.create(estudiante=user, nivel=nivel_seleccionado)

        # 4. Limpiamos la sesión temporal
        del request.session['registro_temporal']

        # 5. Logueamos y redirigimos
        login(request, user)
        messages.success(request, '¡Cuenta creada con éxito!')
        return redirect('inicio')

    return render(request, 'estudiante/configurar_nivel.html')

@login_required
def unirse_clase(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()

        try:
            clase_nueva = Clase.objects.get(codigo=codigo)

            # Buscamos o creamos su registro de solicitud
            solicitud, created = SolicitudClase.objects.get_or_create(
                estudiante=request.user,
                clase=clase_nueva,
                defaults={'estado': 'pendiente', 'intentos': 1}
            )

            # Si está bloqueado permanentemente
            if solicitud.bloqueado:
                messages.error(request, 'Has agotado tus 2 oportunidades en esta clase y estás bloqueado permanentemente.')
                return redirect('estudiante:explorar_clases')

            # Si ya está dentro de la clase
            if request.user in clase_nueva.estudiantes.all():
                messages.warning(request, 'Ya estás en esta clase.')
                return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_nueva.id)

            # Si la solicitud fue rechazada previamente y vuelve a intentarlo
            if not created and solicitud.estado == 'rechazada':
                if solicitud.intentos < 2:
                    solicitud.intentos += 1
                    solicitud.estado = 'pendiente'
                    solicitud.save()
                    messages.success(request, f'Nueva solicitud enviada. Intento de curso: {solicitud.intentos}/2')
                else:
                    solicitud.bloqueado = True
                    solicitud.save()
                    messages.error(request, 'Has agotado tus 2 oportunidades de cursar esta clase.')
                    return redirect('estudiante:explorar_clases')
            else:
                messages.success(request, f'¡Solicitud enviada para la clase "{clase_nueva.nombre}"!')

            return redirect('estudiante:explorar_clases')

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
        clase_solicitada = get_object_or_404(Clase, id=clase_id)

        # Validamos si ya tiene otra clase en la misma categoría de tema
        clases_misma_categoria = request.user.clases_estudiante.filter(categoria_tema=clase_solicitada.categoria_tema)

        if request.user in clase_solicitada.estudiantes.all():
            messages.warning(request, 'Ya estás en esta clase.')
        elif clases_misma_categoria.exists():
            messages.error(request, f'Ya tienes una clase en la categoría "{clase_solicitada.get_categoria_tema_display()}".')
        elif SolicitudClase.objects.filter(clase=clase_solicitada, estudiante=request.user, estado='pendiente').exists():
            messages.warning(request, 'Ya tienes una solicitud pendiente para esta clase.')
        else:
            SolicitudClase.objects.create(clase=clase_solicitada, estudiante=request.user)
            messages.success(request, f'Solicitud enviada a "{clase_solicitada.nombre}". Espera que el docente la acepte.')
            
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
        
    clase = get_object_or_404(Clase, id=clase_id)
    
    if request.user not in clase.estudiantes.all():
        messages.error(request, "No tienes acceso a esta clase o ha sido bloqueada por límite de reprobaciones.")
        return redirect('estudiante:dashboard')
    
    ejercicios = clase.ejercicios.all()

    # Recorremos los ejercicios para calcular los intentos por ejercicio
    for ejercicio in ejercicios:
        ejercicio.mi_intento = ejercicio.intentos.filter(estudiante=request.user).first()
        ejercicio.total_intentos = ejercicio.intentos.filter(estudiante=request.user).count()

    # 🔍 Obtenemos la solicitud general de la clase (para los intentos de inscripción/curso)
    solicitud = SolicitudClase.objects.filter(estudiante=request.user, clase=clase).first()

    return render(request, 'estudiante/detalle_clase_estudiante.html', {
        'clase': clase,
        'ejercicios': ejercicios,
        'solicitud': solicitud, # 👈 Esta variable es clave
    })
    
@login_required
def mis_calificaciones_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    
    # 🟢 Solución directa: Buscamos las clases filtrando por el ManyToManyField 'estudiantes'
    clases = Clase.objects.filter(estudiantes=request.user)
    
    reporte_clases = []
    for clase in clases:
        ejercicios = clase.ejercicios.all().order_by('id')
        
        ejercicios_con_intentos = []
        for ejercicio in ejercicios:
            intento = ejercicio.intentos.filter(estudiante=request.user).first()
            ejercicios_con_intentos.append({
                'ejercicio': ejercicio,
                'intento': intento
            })
            
        reporte_clases.append({
            'clase': clase,
            'ejercicios': ejercicios_con_intentos
        })

    return render(request, 'estudiante/mis_calificaciones.html', {
        'reporte_clases': reporte_clases,
    })

@login_required
def resolver_ejercicio(request, clase_id, ejercicio_id):
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)
    
    if request.method == 'POST':
        preguntas = ejercicio.preguntas.all()
        
        # 1. Creamos el intento como pendiente (sin calificación automática)
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio,
            calificacion=None,      # Sin nota aún
            aprobado=False          # Pendiente de revisión
        )
        
        # 2. Guardamos las respuestas del estudiante para que el docente las vea después
        for pregunta in preguntas:
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                opcion_seleccionada = Opcion.objects.filter(id=opcion_id, pregunta=pregunta).first()
                if opcion_seleccionada:
                    RespuestaEstudiante.objects.create(
                        intento=intento,
                        pregunta=pregunta,
                        opcion_seleccionada=opcion_seleccionada
                    )
            
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_id)

    return render(request, 'estudiante/resolver_ejercicio.html', {
        'ejercicio': ejercicio,
        'clase_id': clase_id
    })