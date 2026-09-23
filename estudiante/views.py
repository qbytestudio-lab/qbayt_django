from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.utils import timezone
from django.http import JsonResponse, request
from django.views.decorators.http import require_POST
from django.db.models import Q
import json
import re

from ejercicios.models import Ejercicio, IntentoEjercicio, RespuestaEstudiante
from clase.models import Clase
from docente.models import SolicitudClase
from web.models import Perfil
from notificaciones.services import notificar_solicitud_clase

from estudiante.utils import (
    clases_visibles_estudiante,
    calcular_progreso_clase,
    calcular_promedio_clase,
    estudiante_reprobo_clase,
    puede_unirse_a_clase,
    esta_inscrito_en_otra_igual,
    clases_bloqueadas_para_estudiante,
    DIAS_GRACIA_VENCIDA,
    DIAS_BLOQUEO_REPROBADA,
    DIAS_CLASE_NUEVA,
    NOTA_APROBACION,
)


# ═══════════════════════════════════════════════════════════
# PERFIL DEL ESTUDIANTE
# ═══════════════════════════════════════════════════════════

@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clases = clases_visibles_estudiante(request.user)
    solicitudes = SolicitudClase.objects.filter(estudiante=request.user)

    progreso_clases = []
    for clase in clases:
        progreso_clases.append({
            'clase': clase,
            'porcentaje': calcular_progreso_clase(request.user, clase)
        })

    if progreso_clases:
        progreso_general = round(
            sum(p['porcentaje'] for p in progreso_clases) / len(progreso_clases)
        )
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

    # Construir historial
    historial = []

    for clase in clases:
        historial.append({
            'nombre': clase.nombre,
            'tipo': 'clase',
            'estado': 'activa',
            'docente_nombre': clase.docente.get_full_name() or clase.docente.username,
            'fecha': clase.fecha_creacion,
            'estudiantes_count': clase.estudiantes.count(),
        })

    solicitudes_rechazadas = SolicitudClase.objects.filter(
        estudiante=request.user,
        estado='rechazada'
    ).select_related('clase', 'clase__docente')

    for solicitud in solicitudes_rechazadas:
        if solicitud.clase.esta_expirada:
            continue
        historial.append({
            'nombre': solicitud.clase.nombre,
            'tipo': 'clase',
            'estado': 'eliminada',
            'docente_nombre': solicitud.clase.docente.get_full_name() or solicitud.clase.docente.username,
            'fecha': solicitud.fecha,
            'estudiantes_count': solicitud.clase.estudiantes.count(),
        })

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
        'clases_completadas': 0,
    })


# ═══════════════════════════════════════════════════════════
# UNIRSE / SOLICITAR / SALIR
# ═══════════════════════════════════════════════════════════

@login_required
def unirse_clase(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()

        try:
            clase = Clase.objects.get(codigo=codigo)
        except Clase.DoesNotExist:
            messages.error(request, "El código de acceso es inválido.")
            return redirect('estudiante:explorar_clases')

        if request.user in clase.estudiantes.all():
            messages.warning(request, "Ya estás inscrito en esta clase.")
            return redirect('estudiante:explorar_clases')

        # Validación centralizada
        puede, motivo = puede_unirse_a_clase(request.user, clase)
        if not puede:
            messages.error(request, motivo)
            return redirect('estudiante:explorar_clases')

        clase.estudiantes.add(request.user)

        SolicitudClase.objects.filter(
            clase=clase, estudiante=request.user
        ).update(estado='aceptada')

        messages.success(
            request,
            f"¡Te has inscrito correctamente a la clase '{clase.nombre}'!"
        )

    return redirect('estudiante:explorar_clases')


@login_required
def solicitar_clase(request):
    if request.method == 'POST':
        clase_id = request.POST.get('clase_id')
        clase = get_object_or_404(Clase, id=clase_id)

        if request.user in clase.estudiantes.all():
            messages.warning(request, "Ya estás inscrito en esta clase.")
            return redirect('estudiante:explorar_clases')

        # Validación centralizada
        puede, motivo = puede_unirse_a_clase(request.user, clase)
        if not puede:
            messages.error(request, motivo)
            return redirect('estudiante:explorar_clases')

        solicitud, creado = SolicitudClase.objects.get_or_create(
            estudiante=request.user,
            clase=clase,
            defaults={'estado': 'pendiente'}
        )

        if not creado:
            solicitud.estado = 'pendiente'
            solicitud.save()
            messages.success(
                request,
                f"Se ha vuelto a enviar la solicitud para la clase '{clase.nombre}'."
            )
        else:
            messages.success(
                request,
                f"Solicitud enviada para la clase '{clase.nombre}'. "
                f"Espera la aprobación del docente."
            )

    return redirect('estudiante:explorar_clases')


@login_required
def salir_clase(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clase = get_object_or_404(Clase, id=clase_id)
    clase.estudiantes.remove(request.user)
    messages.success(request, f'Saliste de "{clase.nombre}".')
    return redirect('estudiante:perfil_estudiante')


# ═══════════════════════════════════════════════════════════
# EXPLORAR CLASES
# ═══════════════════════════════════════════════════════════

@login_required
def explorar_clases(request):
    """
    Vista unificada para explorar clases disponibles.
    No muestra clases expiradas (> 5 días vencidas).
    """
    usuario = request.user

    # Clases donde NO está inscrito, NO es docente, NO expiradas
    limite = timezone.now().date() - timedelta(days=DIAS_GRACIA_VENCIDA)
    clases = Clase.objects.exclude(
        estudiantes=usuario
    ).exclude(
        docente=usuario
    ).exclude(
        fecha_fin__lt=limite
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

    # Solicitudes pendientes
    solicitudes_enviadas = SolicitudClase.objects.filter(
        estudiante=usuario,
        estado='pendiente'
    ).values_list('clase_id', flat=True)

    # Solicitudes rechazadas
    solicitudes_rechazadas = SolicitudClase.objects.filter(
        estudiante=usuario,
        estado='rechazada'
    ).values_list('clase_id', flat=True)

    # Clases bloqueadas por reglas de negocio
    bloqueos = clases_bloqueadas_para_estudiante(usuario)

    context = {
        'clases': clases,
        'categorias': getattr(Clase, 'TEMA_CATEGORIAS', []),
        'total_clases': clases.count(),
        'clases_inscritas_ids': clases_inscritas_ids,
        'solicitudes_enviadas': solicitudes_enviadas,
        'solicitudes_rechazadas': solicitudes_rechazadas,
        'bloqueos': bloqueos,
    }

    return render(request, 'estudiante/explorar_clases.html', context)


# ═══════════════════════════════════════════════════════════
# DETALLE DE CLASE
# ═══════════════════════════════════════════════════════════

@login_required
def detalle_clase_estudiante(request, clase_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clase = get_object_or_404(Clase, id=clase_id)

    # Validación: inscripción
    if request.user not in clase.estudiantes.all():
        messages.error(request, "No tienes acceso a esta clase o aún no estás inscrito.")
        return redirect('estudiante:explorar_clases')

    ejercicios = clase.ejercicios.all()

    for ejercicio in ejercicios:
        ejercicio.mi_intento = ejercicio.intentos.filter(estudiante=request.user).first()
        ejercicio.total_intentos = ejercicio.intentos.filter(estudiante=request.user).count()

    solicitud = SolicitudClase.objects.filter(estudiante=request.user, clase=clase).first()

    return render(request, 'estudiante/detalle_clase_estudiante.html', {
        'clase': clase,
        'ejercicios': ejercicios,
        'solicitud': solicitud,
        'clase_bloqueada': clase.esta_bloqueada,
        'motivo_bloqueo': clase.motivo_bloqueo,
    })


# ═══════════════════════════════════════════════════════════
# MIS CALIFICACIONES
# ═══════════════════════════════════════════════════════════

@login_required
def mis_calificaciones_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clases = clases_visibles_estudiante(request.user)

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


# ═══════════════════════════════════════════════════════════
# MIS CLASES
# ═══════════════════════════════════════════════════════════

@login_required
def mis_clases(request):
    """Lista de clases del estudiante."""
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clases = clases_visibles_estudiante(request.user)

    progreso_clases = []
    for clase in clases:
        progreso_clases.append({
            'clase': clase,
            'porcentaje': calcular_progreso_clase(request.user, clase),
        })

    return render(request, 'estudiante/mis_clases.html', {
        'progreso_clases': progreso_clases,
        'total_clases': clases.count(),
    })


# ═══════════════════════════════════════════════════════════
# SUBIR FOTO DE PERFIL / BANNER
# ═══════════════════════════════════════════════════════════

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

        perfil, created = Perfil.objects.get_or_create(user=request.user)

        perfil.foto_perfil.save(foto.name, foto, save=True)

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
                return JsonResponse({
                    'success': False,
                    'error': 'El archivo debe ser una imagen.'
                })

            if banner.size > 10 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'La imagen no debe superar los 10MB.'
                })

            request.user.perfil.banner = banner
            request.user.perfil.save()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'No se recibió imagen.'})


# ═══════════════════════════════════════════════════════════
# RESOLVER EJERCICIO
# ═══════════════════════════════════════════════════════════

@login_required
def resolver_ejercicio(request, clase_id, ejercicio_id):
    from ejercicios.models import Ejercicio, Pregunta, IntentoEjercicio

    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)

    # ═══════════════════════════════════════════════════
    # VALIDACIONES COMUNES
    # ═══════════════════════════════════════════════════

    if request.user not in clase.estudiantes.all():
        messages.error(request, 'No estás inscrito en esta clase.')
        return redirect('inicio')

    if not ejercicio.activo:
        messages.error(request, 'Este ejercicio está desactivado por el docente.')
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

    if ejercicio.esta_vencido:
        messages.error(
            request,
            f'La fecha límite para este ejercicio venció el '
            f'{ejercicio.fecha_limite.strftime("%d/%m/%Y a las %H:%M")}.'
        )
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

    intento_existente = IntentoEjercicio.objects.filter(
        estudiante=request.user,
        ejercicio=ejercicio
    ).first()

    if intento_existente:
        messages.warning(request, 'Ya enviaste este ejercicio. Está pendiente de revisión.')
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

    # ═══════════════════════════════════════════════════
    # ENRUTADOR POR TIPO
    # ═══════════════════════════════════════════════════

    # ─── Módulo de Escalas ───
    if ejercicio.tipo == 'escalas':
        preguntas_data = []
        raw_contenido = getattr(ejercicio, 'contenido', None)
        if raw_contenido:
            try:
                temp = raw_contenido
                while isinstance(temp, str):
                    temp = json.loads(temp)
                preguntas_data = temp if isinstance(temp, list) else []
            except Exception:
                preguntas_data = []

        return render(request, 'estudiante/resolver_escalas.html', {
            'ejercicio': ejercicio,
            'clase': clase,
            'preguntas_json': preguntas_data,
            'total_preguntas': len(preguntas_data),
        })

    # ─── Módulo de Intervalos ───
    if ejercicio.tipo == 'intervalos':
        preguntas_data = []
        raw_contenido = getattr(ejercicio, 'contenido', None)
        if raw_contenido:
            try:
                temp = raw_contenido
                while isinstance(temp, str):
                    temp = json.loads(temp)
                preguntas_data = temp if isinstance(temp, list) else []
            except Exception:
                preguntas_data = []

        return render(request, 'estudiante/resolver_intervalos.html', {
            'ejercicio': ejercicio,
            'clase': clase,
            'preguntas_json': preguntas_data,
            'total_preguntas': len(preguntas_data),
        })

    # ─── Módulo de Acordes ───
    if ejercicio.tipo == 'acordes':
        preguntas_data = []

        campos_posibles = [
            'contenido', 'contenido_preguntas', 'preguntas_json',
            'config_auditivo', 'datos', 'descripcion_detallada'
        ]

        raw_contenido = None
        for campo in campos_posibles:
            if hasattr(ejercicio, campo):
                val = getattr(ejercicio, campo)
                if val:
                    raw_contenido = val
                    break

        if raw_contenido is not None:
            try:
                temp = raw_contenido
                while isinstance(temp, str):
                    temp = json.loads(temp)

                if isinstance(temp, list):
                    preguntas_data = temp
                elif isinstance(temp, dict):
                    preguntas_data = temp.get('preguntas', [])
            except Exception as err:
                print(f"[ERROR JSON]: No se pudo parsear el contenido: {err}")
                preguntas_data = []

        # Fallback: buscar en tabla Pregunta
        if not preguntas_data:
            from ejercicios.models import Pregunta
            preguntas_rel = Pregunta.objects.filter(ejercicio=ejercicio).prefetch_related('opciones')
            if preguntas_rel.exists():
                for p in preguntas_rel:
                    opts = [{'texto': o.texto, 'correcta': o.es_correcta} for o in p.opciones.all()]
                    preguntas_data.append({
                        'id': p.id,
                        'enunciado': p.texto,
                        'acorde': p.texto,
                        'semitonos': [0, 4, 7],
                        'rootIdx': 0,
                        'opciones': opts
                    })

        for idx, item in enumerate(preguntas_data):
            if not isinstance(item, dict):
                continue
            if 'id' not in item:
                item['id'] = idx + 1
            if 'semitonos' not in item or not item['semitonos']:
                item['semitonos'] = [0, 4, 7]
            if 'rootIdx' not in item:
                item['rootIdx'] = 0

        octava_val = getattr(ejercicio, 'octava', 4) or 4
        try:
            octava_val = int(octava_val)
        except (ValueError, TypeError):
            octava_val = 4

        return render(request, 'estudiante/resolver_acordes.html', {
            'ejercicio': ejercicio,
            'clase': clase,
            'preguntas_json': preguntas_data,
            'total_preguntas': len(preguntas_data),
            'octava_base': octava_val,
        })

    # ─── Entrenamiento Auditivo ───
    if ejercicio.tipo == 'entrenamiento_auditivo':
        return render(request, 'ejercicios/resolver_entrenamiento_auditivo.html', {
            'ejercicio': ejercicio,
            'clase': clase,
        })

    # ─── Entrenamiento Avanzado ───
    if ejercicio.tipo == 'entrenamiento_avanzado':
        return render(request, 'ejercicios/resolver_entrenamiento_avanzado.html', {
            'ejercicio': ejercicio,
            'clase': clase,
        })

    # ─── Juego ───
    if ejercicio.tipo == 'juego':
        if request.method == 'POST':
            IntentoEjercicio.objects.create(
                estudiante=request.user,
                ejercicio=ejercicio,
            )
            messages.success(request, 'Juego enviado. Espera la calificación.')
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

        return render(request, 'estudiante/resolver_juego.html', {
            'ejercicio': ejercicio,
            'clase_id': clase_id,
            'clase': clase,
        })

    # ═══════════════════════════════════════════════════
    # RESTO DE TIPOS (quiz, video_quiz, texto, verdadero_falso, completar)
    # ═══════════════════════════════════════════════════

    preguntas = Pregunta.objects.filter(ejercicio=ejercicio).prefetch_related('opciones')

    embed_url = None
    if ejercicio.video_url:
        # Regex robusto para capturar ID de YouTube (watch, youtu.be, shorts, embed)
        youtube_regex = (
            r'(?:https?://)?(?:www\.)?'
            r'(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/)|youtu\.be/)'
            r'([a-zA-Z0-9_-]{11})'
        )
        match = re.search(youtube_regex, ejercicio.video_url)
        if match:
            embed_url = f"https://www.youtube.com/embed/{match.group(1)}"

    context = {
        'clase': clase,
        'ejercicio': ejercicio,
        'preguntas': preguntas,
        'embed_url': embed_url,
    }

    return render(request, 'estudiante/resolver_ejercicio.html', context)
    
# ═══════════════════════════════════════════════════════════
# ENVIAR RESPUESTAS DE EJERCICIO
# ═══════════════════════════════════════════════════════════

@login_required
def enviar_respuesta_ejercicio(request, clase_id, ejercicio_id):
    """
    Vista unificada para enviar respuestas de cualquier tipo de ejercicio.
    """
    from ejercicios.models import (
        Ejercicio, Pregunta, IntentoEjercicio,
        RespuestaEstudiante, Opcion
    )

    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)

    if request.user not in clase.estudiantes.all():
        messages.error(request, 'No estás inscrito en esta clase.')
        return redirect('inicio')

    if request.method == 'POST':

        if not ejercicio.activo:
            messages.error(request, 'Este ejercicio está desactivado por el docente.')
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

        if ejercicio.esta_vencido:
            messages.error(
                request,
                f'La fecha límite para este ejercicio venció el '
                f'{ejercicio.fecha_limite.strftime("%d/%m/%Y a las %H:%M")}. '
                f'Ya no puedes enviar respuestas.'
            )
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

        intento_existente = IntentoEjercicio.objects.filter(
            estudiante=request.user,
            ejercicio=ejercicio
        ).first()

        if intento_existente:
            messages.warning(
                request,
                'Ya enviaste este ejercicio. Está pendiente de revisión por el docente.'
            )
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

        intentos_count = IntentoEjercicio.objects.filter(
            estudiante=request.user,
            ejercicio=ejercicio
        ).count()

        if intentos_count >= 2:
            messages.error(request, 'Has agotado tus 2 intentos.')
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

       # ─── Módulos interactivos (Acordes, Intervalos, Escalas) ───
        if ejercicio.tipo in ['acordes', 'intervalos', 'escalas']:
            intento = IntentoEjercicio.objects.create(
                estudiante=request.user,
                ejercicio=ejercicio,
                fecha_envio=timezone.now(),
                calificacion=None  # <--- ASEGÚRATE DE QUE ESTÉ EN NONE PARA QUE SALGA "PENDIENTE"
            )

            raw_contenido = getattr(ejercicio, 'contenido', None)
            if raw_contenido:
                try:
                    temp = raw_contenido
                    while isinstance(temp, str):
                        temp = json.loads(temp)

                    if isinstance(temp, list):
                        for idx, item in enumerate(temp):
                            p_id = str(item.get('id', idx))
                            respuesta_dada = (
                                request.POST.get(f'pregunta_{p_id}') or
                                request.POST.get(f'pregunta_{idx}')
                            )

                            if respuesta_dada:
                                # Buscamos si la respuesta dada coincide con la opción marcada como correcta
                                es_realmente_correcta = False
                                opciones_lista = item.get('opciones', [])
                                for opt in opciones_lista:
                                    texto_opt = opt.get('texto') if isinstance(opt, dict) else str(opt)
                                    if texto_opt.strip() == respuesta_dada.strip():
                                        if isinstance(opt, dict) and (opt.get('correcta') or opt.get('es_correcta')):
                                            es_realmente_correcta = True
                                        break

                                enunciado_texto = (
                                    item.get('enunciado') or 
                                    item.get('titulo') or 
                                    item.get('pregunta') or 
                                    f'Pregunta interactiva {idx + 1}'
                                )

                                pregunta_virtual, _ = Pregunta.objects.get_or_create(
                                    ejercicio=ejercicio,
                                    enunciado=enunciado_texto
                                )
                                
                                opcion_virtual, _ = Opcion.objects.get_or_create(
                                    pregunta=pregunta_virtual,
                                    texto_opcion=respuesta_dada,
                                    defaults={'es_correcta': es_realmente_correcta}
                                )
                                
                                RespuestaEstudiante.objects.create(
                                    intento=intento,
                                    pregunta=pregunta_virtual,
                                    opcion_seleccionada=opcion_virtual
                                )
                except Exception as e:
                    print(f"[ERROR MODULOS INTERACTIVOS]: {e}")

            messages.success(
                request,
                'Tus respuestas han sido enviadas. Está pendiente de revisión por el docente.'
            )
            return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

        # ─── Procesamiento tradicional ───
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio,
            fecha_envio=timezone.now(),
        )

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

        messages.success(
            request,
            'Tus respuestas han sido enviadas. Espera la calificación del docente.'
        )
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

    return redirect(
        'estudiante:resolver_ejercicio',
        clase_id=clase_id,
        ejercicio_id=ejercicio_id
    )