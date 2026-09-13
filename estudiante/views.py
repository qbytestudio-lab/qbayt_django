from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.template import context
from django.utils import timezone
from ejercicios.models import Ejercicio, IntentoEjercicio, RespuestaEstudiante
from clase.models import Clase
from docente.models import SolicitudClase
from web.models import Perfil
from django.http import JsonResponse, request
from django.views.decorators.http import require_POST
import json
from notificaciones.services import notificar_solicitud_clase


def calcular_progreso_clase(estudiante, clase):
    """Devuelve el % de ejercicios completados en una clase."""
    total_ejercicios = Ejercicio.objects.filter(clase=clase).count()
    if total_ejercicios == 0:
        return 0
    
    completados = IntentoEjercicio.objects.filter(
        estudiante=estudiante,
        ejercicio__clase=clase
    ).values('ejercicio').distinct().count()
    
    return round((completados / total_ejercicios) * 100)


@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clases = request.user.clases_estudiante.all()
    solicitudes = SolicitudClase.objects.filter(estudiante=request.user)

    progreso_clases = []
    for clase in clases:
        progreso_clases.append({
            'clase': clase,
            'porcentaje': calcular_progreso_clase(request.user, clase)
        })

    if progreso_clases:
        progreso_general = round(sum(p['porcentaje'] for p in progreso_clases) / len(progreso_clases))
    else:
        progreso_general = 0

    ejercicios_hechos = IntentoEjercicio.objects.filter(
        estudiante=request.user
    ).values('ejercicio').distinct().count()

    ahora = timezone.now()
    
    ejercicios_completados = IntentoEjercicio.objects.filter(
        estudiante=request.user
    ).values_list('ejercicio_id', flat=True).distinct()
    
    pendientes = Ejercicio.objects.filter(
        clase__in=clases,
        fecha_limite__isnull=False,
        fecha_limite__gte=ahora
    ).exclude(id__in=ejercicios_completados).select_related('clase')
    
    pendientes_count = pendientes.count()

    # Construir historial SOLO con clases activas y eliminadas
    historial = []
    
    # Agregar clases activas (todas las clases donde está inscrito)
    for clase in clases:
        historial.append({
            'nombre': clase.nombre,
            'tipo': 'clase',
            'estado': 'activa',
            'docente_nombre': clase.docente.get_full_name() or clase.docente.username,
            'fecha': clase.fecha_creacion,
            'estudiantes_count': clase.estudiantes.count(),
        })
    
    # Agregar solicitudes rechazadas como clases eliminadas
    solicitudes_rechazadas = SolicitudClase.objects.filter(
        estudiante=request.user,
        estado='rechazada'
    ).select_related('clase', 'clase__docente')
    
    for solicitud in solicitudes_rechazadas:
        historial.append({
            'nombre': solicitud.clase.nombre,
            'tipo': 'clase',
            'estado': 'eliminada',
            'docente_nombre': solicitud.clase.docente.get_full_name() or solicitud.clase.docente.username,
            'fecha': solicitud.fecha,
            'estudiantes_count': solicitud.clase.estudiantes.count(),
        })
    
    # Ordenar historial por fecha (más recientes primero)
    historial.sort(key=lambda x: x['fecha'], reverse=True)

    return render(request, 'estudiante/perfil_estudiante.html', {
        'clases': clases,
        'solicitudes': solicitudes,
        'progreso_clases': progreso_clases,
        'progreso_general': progreso_general,
        'ejercicios_hechos': ejercicios_hechos,
        'pendientes': pendientes,
        'pendientes_count': pendientes_count,
        'historial': historial,
        'clases_activas': clases.count(),
        'clases_completadas': 0,  # Por ahora no hay clases completadas
    })



@login_required
def unirse_clase(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        
        try:
            clase = Clase.objects.get(codigo=codigo)
            
            # 🚫 1. RESTRICCIÓN POR TÍTULO: Verificar si ya está inscrito en un curso con el mismo título
            clase_mismo_titulo = Clase.objects.filter(
                nombre__iexact=clase.nombre,
                estudiantes=request.user
            ).exclude(id=clase.id).exists()

            if clase_mismo_titulo:
                messages.error(request, f"No puedes unirte. Ya estás inscrito en otro curso con el título '{clase.nombre}'.")
                return redirect('estudiante:explorar_clases')

            # 2. Verificar si ya está inscrito exactamente en esta misma clase
            if request.user in clase.estudiantes.all():
                messages.warning(request, "Ya estás inscrito en esta clase.")
            else:
                # 3. ¡Inscribir de una vez al estudiante con el código!
                clase.estudiantes.add(request.user)
                
                # Opcional por si tenía alguna solicitud pendiente para esta misma clase
                SolicitudClase.objects.filter(
                    clase=clase, estudiante=request.user
                ).update(estado='aceptada')
                
                messages.success(request, f"¡Te has inscrito correctamente a la clase '{clase.nombre}'!")
                
        except Clase.DoesNotExist:
            messages.error(request, "El código de acceso es inválido.")
            
    return redirect('estudiante:explorar_clases')


@login_required
def solicitar_clase(request):
    if request.method == 'POST':
        clase_id = request.POST.get('clase_id')
        clase = get_object_or_404(Clase, id=clase_id)
        
        # 🚫 RESTRICCIÓN POR TÍTULO: Verificar si ya está inscrito en otro curso con el mismo título
        clase_mismo_titulo = Clase.objects.filter(
            nombre__iexact=clase.nombre,
            estudiantes=request.user
        ).exists()

        if clase_mismo_titulo:
            messages.error(request, f"No puedes solicitar acceso. Ya estás inscrito en otro curso con el título '{clase.nombre}'.")
            return redirect('estudiante:explorar_clases')
        
        if request.user in clase.estudiantes.all():
            messages.warning(request, "Ya estás inscrito en esta clase.")
            return redirect('estudiante:explorar_clases')
            
        solicitud, creado = SolicitudClase.objects.get_or_create(
            estudiante=request.user,
            clase=clase,
            defaults={'estado': 'pendiente'}
        )
        
        if not creado:
            solicitud.estado = 'pendiente'
            solicitud.save()
            messages.success(request, f"Se ha vuelto a enviar la solicitud para la clase '{clase.nombre}'.")
        else:
            messages.success(request, f"Solicitud enviada para la clase '{clase.nombre}'. Espera la aprobación del docente.")
            
    return redirect('estudiante:explorar_clases')

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
    """
    Vista unificada para explorar clases disponibles
    """
    from docente.models import SolicitudClase, Clase
    
    usuario = request.user
    
    # Clases donde el usuario NO está inscrito y NO es docente
    clases = Clase.objects.exclude(
        estudiantes=usuario
    ).exclude(
        docente=usuario
    )
    
    # Filtros por categoría
    categoria = request.GET.get('categoria')
    if categoria:
        clases = clases.filter(categoria_tema=categoria)
    
    # Búsqueda
    query = request.GET.get('q')
    if query:
        clases = clases.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query)
        )
    
    # IDs de clases donde el usuario ya está inscrito
    clases_inscritas_ids = usuario.clases_estudiante.values_list('id', flat=True)

    # SOLO solicitudes PENDIENTES
    solicitudes_enviadas = SolicitudClase.objects.filter(
        estudiante=usuario,
        estado='pendiente'
    ).values_list('clase_id', flat=True)
    
    # Solicitudes RECHAZADAS
    solicitudes_rechazadas = SolicitudClase.objects.filter(
        estudiante=usuario,
        estado='rechazada'
    ).values_list('clase_id', flat=True)
    
    context = {
        'clases': clases,
        'categorias': getattr(Clase, 'TEMA_CATEGORIAS', []),
        'total_clases': clases.count(),
        'clases_inscritas_ids': clases_inscritas_ids,
        'solicitudes_enviadas': solicitudes_enviadas,
        'solicitudes_rechazadas': solicitudes_rechazadas,
    }
    
    return render(request, 'estudiante/explorar_clases.html', context)

@login_required
def detalle_clase_estudiante(request, clase_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
        
    clase = get_object_or_404(Clase, id=clase_id)
    
    if request.user not in clase.estudiantes.all():
        messages.error(request, "No tienes acceso a esta clase o aún no estás inscrito.")
        return redirect('estudiante:mis_clases')
    
    # 🟢 TRAEMOS TODOS LOS EJERCICIOS (activos e inactivos)
    ejercicios = clase.ejercicios.all()

    for ejercicio in ejercicios:
        ejercicio.mi_intento = ejercicio.intentos.filter(estudiante=request.user).first()
        ejercicio.total_intentos = ejercicio.intentos.filter(estudiante=request.user).count()

    solicitud = SolicitudClase.objects.filter(estudiante=request.user, clase=clase).first()

    return render(request, 'estudiante/detalle_clase_estudiante.html', {
        'clase': clase,
        'ejercicios': ejercicios,
        'solicitud': solicitud,
    })

@login_required
def mis_calificaciones_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    
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
    
    # 🚫 1. Validar si el ejercicio está inactivo
    if not getattr(ejercicio, 'activo', True):
        messages.error(request, 'Este ejercicio no está disponible en este momento.')
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_id)
    
    # ⏳ 2. VALIDAR SI YA EXISTE UN INTENTO ENVIADO (PENDIENTE)
    # Buscamos si el estudiante ya envió este ejercicio y aún no ha sido aprobado/rechazado (o simplemente tiene un intento previo)
    intento_existente = IntentoEjercicio.objects.filter(
        estudiante=request.user, 
        ejercicio=ejercicio
    ).first()

    if intento_existente:
        # Si ya fue enviado, impedimos resolverlo de nuevo y avisamos que está pendiente
        messages.warning(request, 'Ya has enviado este ejercicio anteriormente. Está pendiente de revisión por el docente.')
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_id)

    # ─── SI ES UN JUEGO, RENDERIZA LA PLANTILLA DE JUEGOS ───
    if ejercicio.tipo == 'juego':
        if request.method == 'POST':
            # Guardar el intento del juego marcándolo como enviado
            IntentoEjercicio.objects.create(
                estudiante=request.user, 
                ejercicio=ejercicio,
                fecha_envio=timezone.now()
            )
            messages.success(request, 'Juego enviado correctamente. Espera la calificación.')
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_id)
            
        return render(request, 'estudiante/resolver_juego.html', {
            'ejercicio': ejercicio,
            'clase_id': clase_id
        })

    # ─── RESTO DE LA LÓGICA PARA QUIZZES Y OTROS ───
    if request.method == 'POST':
        # Crear el intento principal asociado al estudiante y ejercicio
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio,
            fecha_envio=timezone.now()
        )
        
        preguntas = ejercicio.preguntas.all()
        for pregunta in preguntas:
            respuesta_valor = request.POST.get(f'pregunta_{pregunta.id}')
            if respuesta_valor:
                RespuestaEstudiante.objects.create(
                    estudiante=request.user,
                    pregunta=pregunta,
                    respuesta_seleccionada=str(respuesta_valor),
                    es_correcta=False
                )
            
        messages.success(request, 'Ejercicio enviado con éxito. Estado: Pendiente de calificación.')
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_id)

    return render(request, 'estudiante/resolver_ejercicio.html', {
        'ejercicio': ejercicio,
        'clase_id': clase_id
    })

@login_required
@require_POST
def subir_foto_perfil(request):
    try:
        foto = request.FILES.get('foto_perfil')

        if not foto:
            return JsonResponse({
                'success': False,
                'error': 'No se recibió imagen'
            })

        perfil, created = Perfil.objects.get_or_create(
            user=request.user
        )

        perfil.foto_perfil.save(
            foto.name,
            foto,
            save=True
        )

        return JsonResponse({
            'success': True,
            'url': perfil.foto_perfil.url
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def subir_banner(request):
    if request.method == 'POST' and request.FILES.get('banner'):
        try:
            banner = request.FILES['banner']
            
            if not banner.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'El archivo debe ser una imagen.'})
            
            if banner.size > 10 * 1024 * 1024:
                return JsonResponse({'success': False, 'error': 'La imagen no debe superar los 10MB.'})
            
            request.user.perfil.banner = banner
            request.user.perfil.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'No se recibió imagen.'})


@login_required
def resolver_ejercicio(request, clase_id, ejercicio_id):
    """
    Vista unificada para resolver cualquier tipo de ejercicio
    """
    from docente.models import Clase
    from ejercicios.models import Ejercicio, Pregunta, IntentoEjercicio
    from django.utils import timezone
    import re
    
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    # Verificar inscripción
    if request.user not in clase.estudiantes.all():
        messages.error(request, 'No estás inscrito en esta clase.')
        return redirect('inicio')
    
    # Obtener preguntas con opciones
    preguntas = Pregunta.objects.filter(
        ejercicio=ejercicio
    ).prefetch_related('opciones')
    
    # Convertir URL de YouTube a embed
    embed_url = None
    if ejercicio.video_url:
        match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', ejercicio.video_url)
        if match:
            video_id = match.group(1)
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            print(f"DEBUG - Video ID: {video_id}")
            print(f"DEBUG - Embed URL: {embed_url}")
        else:
            print(f"DEBUG - No se pudo extraer ID de: {ejercicio.video_url}")
    
    context = {
        'clase': clase,
        'ejercicio': ejercicio,
        'preguntas': preguntas,
        'embed_url': embed_url,
    }
    
    return render(request, 'estudiante/resolver_ejercicio.html', context)


@login_required
def enviar_respuesta_ejercicio(request, clase_id, ejercicio_id):
    """
    Vista unificada para enviar respuestas de cualquier tipo de ejercicio
    """
    from docente.models import Clase
    from ejercicios.models import Ejercicio, Pregunta, IntentoEjercicio, RespuestaEstudiante, Opcion
    from django.utils import timezone
    
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    if request.method == 'POST':
        # Verificar intentos
        intentos_count = IntentoEjercicio.objects.filter(
            estudiante=request.user,
            ejercicio=ejercicio
        ).count()
        
        if intentos_count >= 2:
            messages.error(request, 'Has agotado tus 2 intentos.')
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)
        
        # Crear intento
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio,
            fecha_envio=timezone.now(),
        )
        
        # Procesar respuestas
        preguntas = Pregunta.objects.filter(ejercicio=ejercicio)
        
        for pregunta in preguntas:
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            
            if opcion_id:
                try:
                    opcion = Opcion.objects.get(id=opcion_id, pregunta=pregunta)
                    RespuestaEstudiante.objects.create(
                        intento=intento,
                        pregunta=pregunta,
                        opcion_seleccionada=opcion,
                    )
                except Opcion.DoesNotExist:
                    pass
        
        messages.success(request, 'Tus respuestas han sido enviadas. Espera la calificación del docente.')
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)
    
    return redirect('estudiante:resolver_ejercicio', clase_id=clase_id, ejercicio_id=ejercicio_id)