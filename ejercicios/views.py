from decimal import Decimal, InvalidOperation
from multiprocessing import context
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from datetime import datetime
from django.utils import timezone
from .models import (Ejercicio, Pregunta, Opcion, IntentoEjercicio, RespuestaEstudiante, PracticaAuditiva, PracticaLibre)
from clase.models import Clase
from docente.models import RecursoMusical
from notificaciones.services import notificar_nuevo_ejercicio, notificar_calificacion
from django.http import JsonResponse, HttpResponse, request
from django.views.decorators.http import require_POST
from decimal import Decimal
import json
from collections import defaultdict


# ============================================================
# VISTA GENERAL / ENRUTADOR PARA CREAR EJERCICIO
# ============================================================
def crear_ejercicio(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    tipo = request.GET.get('tipo', 'quiz')

    if tipo == 'quiz':
        return redirect('ejercicios:crear_quiz', clase_id=clase.id)
    elif tipo == 'acordes': # <-- NUEVO ENRUTAMIENTO
        return redirect('ejercicios:crear_acordes', clase_id=clase.id)
    elif tipo == 'juego':
        return redirect('ejercicios:crear_juego', clase_id=clase.id)
    elif tipo == 'texto':
        return redirect('ejercicios:crear_texto', clase_id=clase.id)
    elif tipo == 'verdadero_falso':
        return redirect('ejercicios:crear_verdadero_falso', clase_id=clase.id)
    elif tipo == 'completar':
        return redirect('ejercicios:crear_completar', clase_id=clase.id)
    elif tipo == 'entrenamiento_auditivo':                                    
        return redirect('ejercicios:crear_entrenamiento_auditivo', clase_id=clase.id)

    return render(request, 'ejercicios/crear_quiz.html', {'clase': clase})

@login_required
def toggle_estado_ejercicio(request, ejercicio_id):
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)
    
    # Validar que el usuario sea el docente dueño de la clase o superusuario
    if request.user != ejercicio.clase.docente and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para modificar este ejercicio.")
        return redirect('inicio')
    
    # Alternar el estado booleano
    ejercicio.activo = not ejercicio.activo
    ejercicio.save()
    
    estado_texto = "activado" if ejercicio.activo else "desactivado"
    messages.success(request, f"El ejercicio ha sido {estado_texto} correctamente.")
    
    return redirect('editar_ejercicio', clase_id=ejercicio.clase.id, ejercicio_id=ejercicio.id)
# ============================================================
# CREAR EJERCICIO ACORDES
# ============================================================

@login_required
def crear_ejercicio_acordes(request, clase_id):
    from docente.models import Clase
    from ejercicios.models import Ejercicio
    from django.utils.dateparse import parse_datetime
    import json

    clase = get_object_or_404(Clase, id=clase_id)

    if clase.docente != request.user:
        messages.error(request, 'No tienes permiso para crear ejercicios en esta clase.')
        return redirect('docente:detalle_clase', clase_id=clase.id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion', '')
        octava = request.POST.get('octava', '4')
        fecha_limite_str = request.POST.get('fecha_limite')
        contenido_json = request.POST.get('contenido_preguntas')

        # ─── SANEAMIENTO PARA EL ESTUDIANTE ───
        if contenido_json:
            try:
                preguntas_list = json.loads(contenido_json)
                for p in preguntas_list:
                    p['enunciado'] = "Identifica el acorde reproducido"
                contenido_json = json.dumps(preguntas_list)
            except Exception:
                pass

        fecha_limite = parse_datetime(fecha_limite_str) if fecha_limite_str else None

        ejercicio = Ejercicio(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='acordes',
            fecha_limite=fecha_limite,
            activo=True
        )

        if hasattr(ejercicio, 'contenido'):
            ejercicio.contenido = contenido_json
        elif hasattr(ejercicio, 'contenido_preguntas'):
            ejercicio.contenido_preguntas = contenido_json

        if hasattr(ejercicio, 'octava'):
            ejercicio.octava = int(octava)

        ejercicio.save()

        messages.success(request, '¡Ejercicio de acordes creado con éxito!')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_acordes.html', {
        'clase': clase,
    })


# ============================================================
# CREAR EJERCICIO INTERVALOS
# ============================================================

@login_required
def crear_ejercicio_intervalos(request, clase_id):
    from docente.models import Clase
    from ejercicios.models import Ejercicio
    from django.utils.dateparse import parse_datetime
    import json

    clase = get_object_or_404(Clase, id=clase_id)

    if clase.docente != request.user:
        messages.error(request, 'No tienes permiso para crear ejercicios en esta clase.')
        return redirect('docente:detalle_clase', clase_id=clase.id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion', '')
        fecha_limite_str = request.POST.get('fecha_limite')
        contenido_json = request.POST.get('contenido_preguntas')

        # ─── SANEAMIENTO PARA EL ESTUDIANTE ───
        if contenido_json:
            try:
                preguntas_list = json.loads(contenido_json)
                for p in preguntas_list:
                    p['enunciado'] = "Identifica el intervalo auditivo reproducido"
                contenido_json = json.dumps(preguntas_list)
            except Exception:
                pass

        fecha_limite = parse_datetime(fecha_limite_str) if fecha_limite_str else None

        Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='intervalos',
            contenido=contenido_json,
            fecha_limite=fecha_limite,
            activo=True
        )

        messages.success(request, '¡Ejercicio de intervalos creado exitosamente!')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_intervalos.html', {
        'clase': clase,
    })


# ============================================================
# CREAR EJERCICIO ESCALAS
# ============================================================

@login_required
def crear_ejercicio_escalas(request, clase_id):
    from docente.models import Clase
    from ejercicios.models import Ejercicio
    from django.utils.dateparse import parse_datetime
    import json

    clase = get_object_or_404(Clase, id=clase_id)

    if clase.docente != request.user:
        messages.error(request, 'No tienes permiso para crear ejercicios en esta clase.')
        return redirect('docente:detalle_clase', clase_id=clase.id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion', '')
        fecha_limite_str = request.POST.get('fecha_limite')
        contenido_json = request.POST.get('contenido_preguntas')

        # ─── SANEAMIENTO PARA EL ESTUDIANTE ───
        if contenido_json:
            try:
                preguntas_list = json.loads(contenido_json)
                for p in preguntas_list:
                    p['enunciado'] = "Identifica la escala reproducida"
                contenido_json = json.dumps(preguntas_list)
            except Exception:
                pass

        fecha_limite = parse_datetime(fecha_limite_str) if fecha_limite_str else None

        Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='escalas',
            contenido=contenido_json,
            fecha_limite=fecha_limite,
            activo=True
        )

        messages.success(request, '¡Ejercicio de escalas creado con éxito!')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_escalas.html', {
        'clase': clase,
    })
# ============================================================
# CREAR EJERCICIO (QUIZ O VIDEO-QUIZ UNIFICADO)
# ============================================================
@login_required
def crear_quiz(request, clase_id):
    """
    Vista unificada para crear un Quiz o un Video + Quiz con preguntas 
    de selección múltiple o verdadero/falso y opciones dinámicas.
    """
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite = request.POST.get('fecha_limite')
        video_principal = request.FILES.get('video_principal')
        video_url = request.POST.get('video_url', '').strip()
        
        # Validaciones básicas
        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        if not fecha_limite:
            messages.error(request, 'La fecha límite es obligatoria.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        try:
            fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        ahora = timezone.now()
        if fecha_limite_dt < ahora.replace(tzinfo=None):
            messages.error(request, 'No puedes usar una fecha límite pasada.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        if video_principal and video_principal.size > 100 * 1024 * 1024:
            messages.error(request, 'El video no debe superar los 100MB.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        # Determinar el tipo de ejercicio automáticamente
        tipo_ejercicio = 'video_quiz' if (video_principal or video_url) else 'quiz'
        
        # Crear el ejercicio principal
        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo_ejercicio,
            fecha_limite=fecha_limite_dt,
            video_principal=video_principal if video_principal else None,
            video_url=video_url if video_url else None,
        )
        
        # Guardar recursos de apoyo seleccionados
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)
        
        # Procesar preguntas dinámicas
        pregunta_ids = []
        for key in request.POST.keys():
            if key.startswith('pregunta_'):
                parts = key.split('_')
                if len(parts) == 2 and parts[1].isdigit():
                    num = int(parts[1])
                    if num not in pregunta_ids:
                        pregunta_ids.append(num)
        
        pregunta_ids.sort()
        
        for i in pregunta_ids:
            texto_pregunta = request.POST.get(f'pregunta_{i}', '').strip()
            imagen_pregunta = request.FILES.get(f'imagen_pregunta_{i}')
            
            if not texto_pregunta:
                continue
            
            pregunta = Pregunta.objects.create(
                ejercicio=ejercicio,
                enunciado=texto_pregunta,
                imagen=imagen_pregunta if imagen_pregunta else None
            )
            
            opcion_correcta_index = request.POST.get(f'correcta_{i}')
            
            # Capturar dinámicamente cuántas opciones llegaron para esta pregunta
            j = 1
            while f'opcion_{i}_{j}' in request.POST:
                texto_opcion = request.POST.get(f'opcion_{i}_{j}', '').strip()
                
                if texto_opcion:
                    es_correcta = (str(j) == str(opcion_correcta_index))
                    Opcion.objects.create(
                        pregunta=pregunta,
                        texto_opcion=texto_opcion,
                        es_correcta=es_correcta
                    )
                j += 1
        
        # Notificar a los estudiantes de la clase
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)
        
        messages.success(request, f'Ejercicio "{titulo}" creado correctamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)
    
    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_quiz.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })


# ============================================================
# CREAR JUEGO
# ============================================================
@login_required
def crear_juego(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        juego_tipo = request.POST.get('juego_tipo', '').strip()

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(request.path)

        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            juego_tipo=juego_tipo,
            tipo='juego'
        )
        
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Juego creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_juego.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })


# ============================================================
# CREAR TEXTO
# ============================================================
@login_required
def crear_texto(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        contenido = request.POST.get('contenido', '').strip()
        imagen = request.FILES.get('imagen')

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(request.path)

        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            contenido=contenido,
            imagen_principal=imagen,
            tipo='texto'
        )
        
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Texto creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_texto.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })





# ============================================================
# CREAR COMPLETAR
# ============================================================
@login_required
def crear_completar(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(request.path)

        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='completar'
        )
        
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Ejercicio de completar creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_completar.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })


# ============================================================
# EDITAR EJERCICIO
# ============================================================
@login_required
def editar_ejercicio(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite = request.POST.get('fecha_limite')
        video_url = request.POST.get('video_url', '').strip()
        video_principal = request.FILES.get('video_principal')
        imagen_principal = request.FILES.get('imagen_principal')
        
        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(f'/clase/detalle/{clase.id}/')
        
        ejercicio.titulo = titulo
        ejercicio.descripcion = descripcion
        
        if fecha_limite:
            try:
                ejercicio.fecha_limite = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(f'/clase/detalle/{clase.id}/')
        else:
            ejercicio.fecha_limite = None
        
        if video_url:
            ejercicio.video_url = video_url
        
        if video_principal:
            ejercicio.video_principal = video_principal
        
        if imagen_principal:
            ejercicio.imagen_principal = imagen_principal
        
        # GUARDAR RECURSOS
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)
        else:
            ejercicio.recursos.clear()
        
        ejercicio.save()
        
        messages.success(request, f'Ejercicio "{titulo}" actualizado correctamente.')
        return redirect(f'/clase/detalle/{clase.id}/')
    
    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    recursos_seleccionados = ejercicio.recursos.all().values_list('id', flat=True)
    
    context = {
        'clase': clase,
        'ejercicio': ejercicio,
        'recursos_disponibles': recursos_disponibles,
        'recursos_seleccionados': recursos_seleccionados,
    }
    
    return render(request, 'docente/editar_ejercicio.html', context)


# ============================================================
# CALIFICAR EJERCICIO
# ============================================================
@login_required
def calificar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
    ejercicio = intento.ejercicio

    # ═══════════════════════════════════════════════════
    # DATOS SEGÚN EL TIPO DE EJERCICIO
    # ═══════════════════════════════════════════════════
    respuestas = []
    practica_auditiva = None

    if ejercicio.tipo == 'entrenamiento_auditivo':
        try:
            practica_auditiva = intento.practica_auditiva
        except PracticaAuditiva.DoesNotExist:
            practica_auditiva = None
    else:
        respuestas_qs = intento.respuestas.select_related(
            'pregunta',
            'opcion_seleccionada'
        ).all()
        
        # Procesar y enriquecer respuestas para módulos interactivos (Acordes, Intervalos, Escalas)
        contenido_json = None
        if ejercicio.tipo in ['acordes', 'intervalos', 'escalas'] and ejercicio.contenido:
            try:
                import json
                temp = ejercicio.contenido
                while isinstance(temp, str):
                    temp = json.loads(temp)
                contenido_json = temp if isinstance(temp, list) else temp.get('preguntas', [])
            except Exception:
                contenido_json = []

        for idx, r in enumerate(respuestas_qs):
            item_data = {
                'pregunta': r.pregunta,
                'opcion_seleccionada': r.opcion_seleccionada,
                'todas_opciones': []
            }
            
            # Si el ejercicio tiene contenido JSON, extraemos las opciones de esta pregunta
            if contenido_json and idx < len(contenido_json):
                preg_json = contenido_json[idx]
                item_data['todas_opciones'] = preg_json.get('opciones', [])
            
            respuestas.append(item_data)

    # ═══════════════════════════════════════════════════
    # POST: GUARDAR CALIFICACIÓN
    # ═══════════════════════════════════════════════════
    if request.method == 'POST':
        nota_str = request.POST.get('calificacion', '').strip()
        retroalimentacion = request.POST.get('retroalimentacion', '').strip()

        if not nota_str:
            messages.error(request, 'Por favor ingresa una calificación.')
            return redirect(request.path)

        try:
            nota = Decimal(nota_str)
        except InvalidOperation:
            messages.error(request, 'La calificación ingresada no es válida.')
            return redirect(request.path)

        if nota < Decimal('1.0') or nota > Decimal('5.0'):
            messages.error(request, 'La calificación debe estar entre 1.0 y 5.0.')
            return redirect(request.path)

        NOTA_MINIMA = Decimal('3.0')

        intento.calificacion = nota
        intento.retroalimentacion = retroalimentacion
        intento.aprobado = nota >= NOTA_MINIMA
        intento.save()

        clase = ejercicio.clase
        estudiante = intento.estudiante

        notificar_calificacion(estudiante, ejercicio, nota)

        total_intentos = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio=ejercicio
        ).count()

        if intento.aprobado:
            messages.success(request, '¡Calificación guardada correctamente! El estudiante aprobó.')
        else:
            if total_intentos < 2:
                messages.warning(
                    request,
                    f'Calificación menor a {NOTA_MINIMA}. El estudiante puede realizar un segundo y último intento.'
                )
            else:
                messages.error(
                    request,
                    f'Calificación menor a {NOTA_MINIMA}. El estudiante ha agotado sus 2 intentos y ha sido bloqueado de la clase.'
                )
                if estudiante in clase.estudiantes.all():
                    clase.estudiantes.remove(estudiante)

        return redirect(
            'ejercicios:detalle_ejercicio_docente',
            clase_id=clase.id,
            ejercicio_id=ejercicio.id
        )

    # ═══════════════════════════════════════════════════
    # GET: RENDERIZAR
    # ═══════════════════════════════════════════════════
    return render(
        request,
        'ejercicios/calificar_ejercicio.html',
        {
            'intento': intento,
            'respuestas': respuestas,
            'practica_auditiva': practica_auditiva,
            'ejercicio': ejercicio,
            'clase': ejercicio.clase,
        }
    )


# ============================================================
# DETALLE EJERCICIO DOCENTE
# ============================================================
@login_required
def detalle_ejercicio_docente(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    intentos = IntentoEjercicio.objects.filter(
        ejercicio=ejercicio
    ).select_related('estudiante').order_by('-fecha_envio')
    
    recursos = ejercicio.recursos.all()

    return render(
        request,
        'ejercicios/detalle_ejercicio_docente.html',
        {
            'clase': clase,
            'ejercicio': ejercicio,
            'intentos': intentos,
            'recursos': recursos,
        }
    )


# ============================================================
# ELIMINAR EJERCICIO
# ============================================================
@login_required
def eliminar_ejercicio(request, clase_id, ejercicio_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
        
    ejercicio = get_object_or_404(
        Ejercicio, 
        id=ejercicio_id, 
        clase_id=clase_id, 
        clase__docente=request.user
    )
    
    ejercicio.delete()
    
    messages.success(request, 'Ejercicio eliminado con éxito.')
    return redirect(f'/clase/detalle/{clase_id}/')


# ============================================================
# REENVIAR EJERCICIO
# ============================================================
@login_required
def reenviar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
    
    clase_id = intento.ejercicio.clase.id
    ejercicio_id = intento.ejercicio.id
    
    intento.respuestas.all().delete()
    intento.delete()
    
    messages.warning(request, "El intento ha sido rechazado. El estudiante ya puede volver a realizar el ejercicio.")
    
    return redirect('ejercicios:detalle_ejercicio_docente', clase_id=clase_id, ejercicio_id=ejercicio_id)

# ============================================================
# CREAR ENTRENAMIENTO AUDITIVO
# ============================================================
@login_required
def crear_entrenamiento_auditivo(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite = request.POST.get('fecha_limite')

        tipo_practica = request.POST.get('tipo_practica', 'intervalos')
        subtipo = request.POST.get('subtipo', 'basico')  # ← NUEVO
        dificultad = request.POST.get('dificultad', 'facil')
        num_preguntas = int(request.POST.get('num_preguntas', 10))
        instrumento = request.POST.get('instrumento', 'piano')

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect('ejercicios:crear_entrenamiento_auditivo', clase_id=clase.id)

        if not fecha_limite:
            messages.error(request, 'La fecha límite es obligatoria.')
            return redirect('ejercicios:crear_entrenamiento_auditivo', clase_id=clase.id)

        try:
            fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('ejercicios:crear_entrenamiento_auditivo', clase_id=clase.id)

        # Crear el ejercicio con subtipo en config_auditivo
        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='entrenamiento_auditivo',
            fecha_limite=fecha_limite_dt,
            config_auditivo={
                'tipo_practica': tipo_practica,
                'subtipo': subtipo,  # ← NUEVO
                'dificultad': dificultad,
                'num_preguntas': num_preguntas,
                'instrumento': instrumento,
            }
        )

        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, f'Entrenamiento auditivo "{titulo}" creado correctamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_entrenamiento_auditivo.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })
@login_required
@require_POST
def guardar_practica_auditiva(request, ejercicio_id):
    """Guarda el resultado de una práctica de entrenamiento auditivo."""
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)

    if ejercicio.tipo != 'entrenamiento_auditivo':
        return JsonResponse({'error': 'Tipo inválido'}, status=400)

    try:
        aciertos = int(request.POST.get('aciertos', 0))
        total = int(request.POST.get('total', 0))
        detalle_raw = request.POST.get('detalle', '[]')
        detalle = json.loads(detalle_raw) if detalle_raw else []
    except (ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)

    # Calificación sobre 5.0 (100% → 5.0, 0% → 1.0)
    if total > 0:
        porcentaje = (aciertos / total) * 100
        nota = round(Decimal(porcentaje) / Decimal(20), 1)
        nota = max(Decimal('1.0'), min(Decimal('5.0'), nota))
    else:
        nota = Decimal('1.0')

    aprobado = nota >= Decimal('3.0')

    try:
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio,
            calificacion=nota,
            aprobado=aprobado,
        )
    except Exception as e:
        return JsonResponse({'error': f'Error al crear intento: {e}'}, status=500)

    # Guardar detalle de la práctica
    try:
        PracticaAuditiva.objects.create(
            intento=intento,
            tipo_practica=ejercicio.config_auditivo.get('tipo_practica', 'intervalos'),
            aciertos=aciertos,
            total_preguntas=total,
            detalle_respuestas=detalle,
        )
    except Exception as e:
        # No rompemos todo si falla el detalle, solo lo logueamos
        import logging
        logging.getLogger(__name__).warning(f'Error guardando PracticaAuditiva: {e}')

    return JsonResponse({
        'success': True,
        'nota': float(nota),
        'aprobado': aprobado,
        'aciertos': aciertos,
        'total': total,
    })

@login_required
def resolver_entrenamiento_auditivo(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(
        Ejercicio,
        id=ejercicio_id,
        clase=clase,
        tipo='entrenamiento_auditivo'
    )
    return render(request, 'ejercicios/resolver_entrenamiento_auditivo.html', {
        'ejercicio': ejercicio,
        'clase': clase,
    })

# ============================================================
# REPORTE DE DEBILIDADES DE LA CLASE (ENTRENAMIENTO AUDITIVO)
# ============================================================
from collections import defaultdict

@login_required
def reporte_debilidades(request, clase_id):
    from docente.models import Clase
    from ejercicios.models import IntentoEjercicio

    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    tipo_filtro = request.GET.get('tipo', 'todos')

    # 1. Prácticas tradicionales
    practicas_qs = PracticaAuditiva.objects.filter(
        intento__ejercicio__clase=clase,
        intento__ejercicio__tipo__in=['entrenamiento_auditivo', 'entrenamiento_avanzado'],
    ).select_related(
        'intento',
        'intento__ejercicio',
        'intento__estudiante',
    )

    if tipo_filtro != 'todos':
        practicas_qs = practicas_qs.filter(tipo_practica=tipo_filtro)

    practicas = list(practicas_qs)

    # 2. Intentos interactivos de la clase
    intentos_interactivos_qs = IntentoEjercicio.objects.filter(
        ejercicio__clase=clase,
        ejercicio__tipo__in=['acordes', 'intervalos', 'escalas']
    ).select_related(
        'ejercicio',
        'estudiante'
    ).prefetch_related('respuestas__pregunta', 'respuestas__opcion_seleccionada')

    if tipo_filtro != 'todos':
        if tipo_filtro in ['acordes', 'intervalos', 'escalas']:
            intentos_interactivos_qs = intentos_interactivos_qs.filter(ejercicio__tipo=tipo_filtro)
        else:
            intentos_interactivos_qs = intentos_interactivos_qs.none()

    intentos_interactivos = list(intentos_interactivos_qs)

    # ─── Estadísticas por tipo ───
    tipos_contador = defaultdict(lambda: {'practicas': 0, 'aciertos': 0, 'total': 0})
    for p in practicas:
        tipos_contador[p.tipo_practica]['practicas'] += 1
        tipos_contador[p.tipo_practica]['aciertos'] += p.aciertos
        tipos_contador[p.tipo_practica]['total'] += p.total_preguntas

    for intento in intentos_interactivos:
        tipo_ej = intento.ejercicio.tipo
        tipos_contador[tipo_ej]['practicas'] += 1
        for resp in intento.respuestas.all():
            tipos_contador[tipo_ej]['total'] += 1
            if resp.opcion_seleccionada and getattr(resp.opcion_seleccionada, 'es_correcta', False):
                tipos_contador[tipo_ej]['aciertos'] += 1

    resumen_tipos = []
    for tipo, data in tipos_contador.items():
        pct = round((data['aciertos'] / data['total']) * 100, 1) if data['total'] > 0 else 0
        resumen_tipos.append({
            'tipo': tipo,
            'label': dict(PracticaAuditiva.TIPO_CHOICES).get(tipo, tipo.capitalize()),
            'practicas': data['practicas'],
            'aciertos': data['aciertos'],
            'total': data['total'],
            'porcentaje': pct,
        })
    resumen_tipos.sort(key=lambda x: x['porcentaje'])

    # ─── Análisis de respuestas ───
    analisis = defaultdict(lambda: {
        'fallos': 0,
        'aciertos': 0,
        'confusiones': defaultdict(int),
    })

    for p in practicas:
        detalle = p.detalle_respuestas or []
        for r in detalle:
            correcta = r.get('correcta', '').strip()
            respuesta = r.get('respuesta', '').strip()
            acerto = r.get('acerto', False)
            if not correcta:
                continue
            if acerto:
                analisis[correcta]['aciertos'] += 1
            else:
                analisis[correcta]['fallos'] += 1
                if respuesta:
                    analisis[correcta]['confusiones'][respuesta] += 1

    for intento in intentos_interactivos:
        for resp in intento.respuestas.all():
            if resp.pregunta:
                target_nombre = resp.pregunta.enunciado
                es_correcta = resp.opcion_seleccionada and getattr(resp.opcion_seleccionada, 'es_correcta', False)
                if es_correcta:
                    analisis[target_nombre]['aciertos'] += 1
                else:
                    analisis[target_nombre]['fallos'] += 1
                    if resp.opcion_seleccionada:
                        analisis[target_nombre]['confusiones'][resp.opcion_seleccionada.texto_opcion] += 1

    debilidades = []
    for nombre, data in analisis.items():
        total = data['fallos'] + data['aciertos']
        if total == 0:
            continue
        pct_error = round((data['fallos'] / total) * 100, 1)
        confusiones_top = sorted(data['confusiones'].items(), key=lambda x: -x[1])[:3]
        debilidades.append({
            'nombre': nombre,
            'total': total,
            'fallos': data['fallos'],
            'aciertos': data['aciertos'],
            'porcentaje_error': pct_error,
            'porcentaje_acierto': round(100 - pct_error, 1),
            'confusiones': [{'respuesta': c[0], 'veces': c[1]} for c in confusiones_top],
        })

    debilidades.sort(key=lambda x: -x['porcentaje_error'])

    a_reforzar = [d for d in debilidades if d['porcentaje_error'] >= 50][:8]
    # Actualizado a total >= 1 para reflejar los aciertos inmediatamente
    dominadas = [d for d in debilidades if d['porcentaje_error'] < 30 and d['total'] >= 1][:8]

    sugerencias = []
    if a_reforzar:
        nombres = ', '.join(d['nombre'] for d in a_reforzar[:3])
        sugerencias.append({
            'icono': 'exclamation-triangle-fill',
            'tipo': 'danger',
            'texto': f'Refuerza en clase: {nombres}'
        })

    if dominadas:
        nombres = ', '.join(d['nombre'] for d in dominadas[:3])
        sugerencias.append({
            'icono': 'check-circle-fill',
            'tipo': 'success',
            'texto': f'La clase domina: {nombres}. Puedes avanzar al siguiente nivel.'
        })

    estudiantes_unicos = set(p.intento.estudiante_id for p in practicas)
    for intento in intentos_interactivos:
        estudiantes_unicos.add(intento.estudiante_id)

    context = {
        'clase': clase,
        'practicas_total': len(practicas) + len(intentos_interactivos),
        'estudiantes_total': len(estudiantes_unicos),
        'resumen_tipos': resumen_tipos,
        'a_reforzar': a_reforzar,
        'dominadas': dominadas,
        'sugerencias': sugerencias,
        'tipo_filtro': tipo_filtro,
        'tipos_disponibles': PracticaAuditiva.TIPO_CHOICES,
    }

    return render(request, 'ejercicios/reporte_debilidades.html', context)
    
# ============================================================
# PANEL GLOBAL DE DEBILIDADES (TODAS LAS CLASES DEL DOCENTE)
# ============================================================
@login_required
def debilidades_global(request):
    """
    Panel global que muestra debilidades auditivas sumando TODAS
    las clases del docente, integrando prácticas tradicionales y módulos interactivos.
    """
    from docente.models import Clase
    from ejercicios.models import IntentoEjercicio, RespuestaEstudiante
    from datetime import timedelta

    # ─── Filtros GET ───
    clase_filtro = request.GET.get('clase', 'todas')
    tipo_filtro = request.GET.get('tipo', 'todos')
    rango_filtro = request.GET.get('rango', '30')

    # ─── Clases del docente ───
    mis_clases = Clase.objects.filter(docente=request.user)

    # ─── Query base de prácticas tradicionales ───
    practicas_qs = PracticaAuditiva.objects.filter(
        intento__ejercicio__clase__docente=request.user,
        intento__ejercicio__tipo__in=['entrenamiento_auditivo', 'entrenamiento_avanzado', 'acordes', 'intervalos', 'escalas'],
    ).select_related(
        'intento',
        'intento__ejercicio',
        'intento__ejercicio__clase',
        'intento__estudiante',
    )

    # Filtro por clase
    if clase_filtro != 'todas':
        practicas_qs = practicas_qs.filter(intento__ejercicio__clase_id=clase_filtro)

    # Filtro por tipo
    if tipo_filtro != 'todos':
        practicas_qs = practicas_qs.filter(tipo_practica=tipo_filtro)

    # Filtro por rango de fechas
    if rango_filtro != 'todo':
        try:
            dias = int(rango_filtro)
            desde = timezone.now() - timedelta(days=dias)
            practicas_qs = practicas_qs.filter(intento__fecha_envio__gte=desde)
        except (ValueError, TypeError):
            pass

    practicas = list(practicas_qs)

    # ═══════════════════════════════════════════════════
    # INTEGRACIÓN DE MÓDULOS INTERACTIVOS (Acordes, Intervalos, Escalas)
    # ═══════════════════════════════════════════════════
    intentos_interactivos_qs = IntentoEjercicio.objects.filter(
        ejercicio__clase__docente=request.user,
        ejercicio__tipo__in=['acordes', 'intervalos', 'escalas'],
        calificacion__isnull=False
    ).select_related(
        'ejercicio',
        'ejercicio__clase',
        'estudiante'
    ).prefetch_related('respuestas__pregunta', 'respuestas__opcion_seleccionada')

    if clase_filtro != 'todas':
        intentos_interactivos_qs = intentos_interactivos_qs.filter(ejercicio__clase_id=clase_filtro)

    if rango_filtro != 'todo':
        try:
            dias = int(rango_filtro)
            desde = timezone.now() - timedelta(days=dias)
            intentos_interactivos_qs = intentos_interactivos_qs.filter(fecha_envio__gte=desde)
        except (ValueError, TypeError):
            pass

    # ═══════════════════════════════════════════════════
    # STATS GLOBALES Y ANÁLISIS DE DEBILIDADES
    # ═══════════════════════════════════════════════════
    estudiantes_unicos = set(p.intento.estudiante_id for p in practicas)
    clases_unicas = set(p.intento.ejercicio.clase_id for p in practicas)

    total_aciertos = sum(p.aciertos for p in practicas)
    total_preguntas = sum(p.total_preguntas for p in practicas)

    # Sumamos también los intentos interactivos calificados
    for intento in intentos_interactivos_qs:
        estudiantes_unicos.add(intento.estudiante_id)
        clases_unicas.add(intento.ejercicio.clase_id)
        # Evaluamos las respuestas interactivas registradas
        for resp in intento.respuestas.all():
            total_preguntas += 1
            # Verificamos si la opción seleccionada era correcta
            if resp.opcion_seleccionada and getattr(resp.opcion_seleccionada, 'es_correcta', False):
                total_aciertos += 1

    practicas_total = len(practicas) + intentos_interactivos_qs.count()
    promedio_global = round((total_aciertos / total_preguntas) * 100, 1) if total_preguntas > 0 else 0

    # ═══════════════════════════════════════════════════
    # ANÁLISIS POR PRÁCTICA (debilidades)
    # ═══════════════════════════════════════════════════
    analisis = defaultdict(lambda: {
        'fallos': 0,
        'aciertos': 0,
        'confusiones': defaultdict(int),
        'clases': set(),
    })

    for p in practicas:
        detalle = p.detalle_respuestas or []
        clase_nombre = p.intento.ejercicio.clase.nombre

        for r in detalle:
            correcta = r.get('correcta', '').strip()
            respuesta = r.get('respuesta', '').strip()
            acerto = r.get('acerto', False)

            if not correcta:
                continue

            analisis[correcta]['clases'].add(clase_nombre)

            if acerto:
                analisis[correcta]['aciertos'] += 1
            else:
                analisis[correcta]['fallos'] += 1
                if respuesta:
                    analisis[correcta]['confusiones'][respuesta] += 1

    # Procesamos también los errores de los módulos interactivos
    for intento in intentos_interactivos_qs:
        clase_nombre = intento.ejercicio.clase.nombre
        for resp in intento.respuestas.all():
            if resp.pregunta:
                target_nombre = resp.pregunta.enunciado
                analisis[target_nombre]['clases'].add(clase_nombre)
                es_correcta = resp.opcion_seleccionada and getattr(resp.opcion_seleccionada, 'es_correcta', False)
                if es_correcta:
                    analisis[target_nombre]['aciertos'] += 1
                else:
                    analisis[target_nombre]['fallos'] += 1
                    if resp.opcion_seleccionada:
                        analisis[target_nombre]['confusiones'][resp.opcion_seleccionada.texto_opcion] += 1

    debilidades = []
    for nombre, data in analisis.items():
        total = data['fallos'] + data['aciertos']
        if total == 0:
            continue
        pct_error = round((data['fallos'] / total) * 100, 1)

        confusiones_top = sorted(
            data['confusiones'].items(),
            key=lambda x: -x[1]
        )[:3]

        debilidades.append({
            'nombre': nombre,
            'total': total,
            'fallos': data['fallos'],
            'aciertos': data['aciertos'],
            'porcentaje_error': pct_error,
            'porcentaje_acierto': round(100 - pct_error, 1),
            'clases': sorted(list(data['clases'])),
            'confusiones': [{'respuesta': c[0], 'veces': c[1]} for c in confusiones_top],
        })

    debilidades.sort(key=lambda x: -x['porcentaje_error'])

    top_debilidades = debilidades[:10]
    dominadas = [d for d in debilidades if d['porcentaje_error'] < 30 and d['total'] >= 3][:8]

    # ═══════════════════════════════════════════════════
    # TOP ESTUDIANTES (Integrando tradicionales e interactivos)
    # ═══════════════════════════════════════════════════
    por_estudiante = defaultdict(lambda: {'aciertos': 0, 'total': 0, 'practicas': 0, 'estudiante': None})
    
    for p in practicas:
        eid = p.intento.estudiante_id
        por_estudiante[eid]['aciertos'] += p.aciertos
        por_estudiante[eid]['total'] += p.total_preguntas
        por_estudiante[eid]['practicas'] += 1
        por_estudiante[eid]['estudiante'] = p.intento.estudiante

    for intento in intentos_interactivos_qs:
        eid = intento.estudiante_id
        por_estudiante[eid]['practicas'] += 1
        por_estudiante[eid]['estudiante'] = intento.estudiante
        for resp in intento.respuestas.all():
            por_estudiante[eid]['total'] += 1
            if resp.opcion_seleccionada and getattr(resp.opcion_seleccionada, 'es_correcta', False):
                por_estudiante[eid]['aciertos'] += 1

    top_estudiantes = []
    for eid, data in por_estudiante.items():
        if data['total'] == 0:
            continue
        pct = round((data['aciertos'] / data['total']) * 100, 1)
        top_estudiantes.append({
            'estudiante': data['estudiante'],
            'porcentaje': pct,
            'practicas': data['practicas'],
        })

    top_estudiantes.sort(key=lambda x: -x['porcentaje'])
    top_estudiantes = top_estudiantes[:5]

    # ═══════════════════════════════════════════════════
    # CONTEXTO
    # ═══════════════════════════════════════════════════
    context = {
        'mis_clases': mis_clases,
        'practicas_total': practicas_total,
        'estudiantes_total': len(estudiantes_unicos),
        'clases_total': len(clases_unicas),
        'promedio_global': promedio_global,
        'top_debilidades': top_debilidades,
        'dominadas': dominadas,
        'top_estudiantes': top_estudiantes,
        'clase_filtro': clase_filtro,
        'tipo_filtro': tipo_filtro,
        'rango_filtro': rango_filtro,
        'tipos_disponibles': PracticaAuditiva.TIPO_CHOICES,
    }

    return render(request, 'ejercicios/debilidades_global.html', context)
# ============================================================
# EXPORTAR REPORTE DE DEBILIDADES A PDF (DISEÑO MEJORADO)
# ============================================================
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.units import cm


@login_required
def exportar_debilidades_pdf(request):
    """Exporta el reporte de debilidades a PDF con diseño profesional."""
    from docente.models import Clase
    from datetime import timedelta

    # ─── Filtros GET ───
    clase_filtro = request.GET.get('clase', 'todas')
    tipo_filtro = request.GET.get('tipo', 'todos')
    rango_filtro = request.GET.get('rango', '30')

    # ─── Clases del docente ───
    mis_clases = Clase.objects.filter(docente=request.user)

    # ─── Query base ───
    practicas_qs = PracticaAuditiva.objects.filter(
        intento__ejercicio__clase__docente=request.user,
        intento__ejercicio__tipo__in=['entrenamiento_auditivo', 'entrenamiento_avanzado'],
    ).select_related(
        'intento',
        'intento__ejercicio',
        'intento__ejercicio__clase',
        'intento__estudiante',
    )

    if clase_filtro != 'todas':
        practicas_qs = practicas_qs.filter(intento__ejercicio__clase_id=clase_filtro)

    if tipo_filtro != 'todos':
        practicas_qs = practicas_qs.filter(tipo_practica=tipo_filtro)

    if rango_filtro != 'todo':
        try:
            dias = int(rango_filtro)
            desde = timezone.now() - timedelta(days=dias)
            practicas_qs = practicas_qs.filter(intento__fecha_envio__gte=desde)
        except (ValueError, TypeError):
            pass

    practicas = list(practicas_qs)

    # ─── Stats ───
    practicas_total = len(practicas)
    estudiantes_unicos = set(p.intento.estudiante_id for p in practicas)
    clases_unicas = set(p.intento.ejercicio.clase_id for p in practicas)
    total_aciertos = sum(p.aciertos for p in practicas)
    total_preguntas = sum(p.total_preguntas for p in practicas)
    promedio_global = round((total_aciertos / total_preguntas) * 100, 1) if total_preguntas > 0 else 0

    # ─── Análisis ───
    analisis = defaultdict(lambda: {
        'fallos': 0, 'aciertos': 0,
        'confusiones': defaultdict(int),
        'clases': set(),
    })

    for p in practicas:
        detalle = p.detalle_respuestas or []
        clase_nombre = p.intento.ejercicio.clase.nombre

        for r in detalle:
            correcta = r.get('correcta', '').strip()
            respuesta = r.get('respuesta', '').strip()
            acerto = r.get('acerto', False)

            if not correcta:
                continue

            analisis[correcta]['clases'].add(clase_nombre)

            if acerto:
                analisis[correcta]['aciertos'] += 1
            else:
                analisis[correcta]['fallos'] += 1
                if respuesta:
                    analisis[correcta]['confusiones'][respuesta] += 1

    debilidades = []
    for nombre, data in analisis.items():
        total = data['fallos'] + data['aciertos']
        if total == 0:
            continue
        pct_error = round((data['fallos'] / total) * 100, 1)
        confusiones_top = sorted(data['confusiones'].items(), key=lambda x: -x[1])[:2]
        debilidades.append({
            'nombre': nombre,
            'total': total,
            'fallos': data['fallos'],
            'aciertos': data['aciertos'],
            'porcentaje_error': pct_error,
            'porcentaje_acierto': round(100 - pct_error, 1),
            'clases': sorted(list(data['clases'])),
            'confusiones': [{'respuesta': c[0], 'veces': c[1]} for c in confusiones_top],
        })

    debilidades.sort(key=lambda x: -x['porcentaje_error'])
    top_debilidades = debilidades[:10]
    dominadas = [d for d in debilidades if d['porcentaje_error'] < 30 and d['total'] >= 3][:6]

    # ─── Comparativa por clase ───
    por_clase = defaultdict(lambda: {'aciertos': 0, 'total': 0, 'practicas': 0})
    for p in practicas:
        cid = p.intento.ejercicio.clase_id
        por_clase[cid]['aciertos'] += p.aciertos
        por_clase[cid]['total'] += p.total_preguntas
        por_clase[cid]['practicas'] += 1

    comparativa_clases = []
    for clase in mis_clases:
        data = por_clase.get(clase.id)
        if not data or data['total'] == 0:
            continue
        pct = round((data['aciertos'] / data['total']) * 100, 1)
        comparativa_clases.append({
            'clase': clase, 'porcentaje': pct,
            'practicas': data['practicas'],
            'aciertos': data['aciertos'], 'total': data['total'],
        })
    comparativa_clases.sort(key=lambda x: x['porcentaje'])

    # ═══════════════════════════════════════════════════
    # GENERAR PDF
    # ═══════════════════════════════════════════════════

    response = HttpResponse(content_type='application/pdf')

    if clase_filtro != 'todas':
        try:
            clase_obj = Clase.objects.get(id=clase_filtro, docente=request.user)
            nombre_archivo = f"debilidades_{clase_obj.nombre.replace(' ', '_')}.pdf"
            subtitulo = clase_obj.nombre
        except Clase.DoesNotExist:
            nombre_archivo = "debilidades_global.pdf"
            subtitulo = "Todas las clases"
    else:
        nombre_archivo = "debilidades_global.pdf"
        subtitulo = "Todas las clases"

    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # ═══════════════════════════════════════════════════
    # COLORES
    # ═══════════════════════════════════════════════════
    C_VERDE = HexColor('#16a34a')
    C_VERDE_CLARO = HexColor('#dcfce7')
    C_VERDE_OSCURO = HexColor('#14532d')
    C_NEGRO = HexColor('#0f172a')
    C_GRIS = HexColor('#64748b')
    C_GRIS_CLARO = HexColor('#f1f5f9')
    C_BLANCO = HexColor('#ffffff')
    C_ROJO = HexColor('#dc2626')
    C_ROJO_CLARO = HexColor('#fee2e2')
    C_AMARILLO = HexColor('#f59e0b')
    C_AMARILLO_CLARO = HexColor('#fef3c7')
    C_MORADO = HexColor('#7c6fff')
    C_CYAN = HexColor('#06b6d4')

    # ═══════════════════════════════════════════════════
    # HEADER CON BANDA VERDE
    # ═══════════════════════════════════════════════════

    # Banda verde superior (más alta)
    p.setFillColor(C_VERDE)
    p.rect(0, height - 120, width, 120, fill=1, stroke=0)

    # Acento oscuro
    p.setFillColor(C_VERDE_OSCURO)
    p.rect(0, height - 120, 8, 120, fill=1, stroke=0)

    # Título
    p.setFillColor(C_BLANCO)
    p.setFont("Helvetica-Bold", 26)
    p.drawString(50, height - 55, "Debilidades Auditivas")

    # Subtítulo
    p.setFillColor(HexColor('#bbf7d0'))
    p.setFont("Helvetica", 13)
    p.drawString(50, height - 80, subtitulo)

    # Fecha
    p.setFillColor(C_BLANCO)
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 100, f"QBYT · Generado el {timezone.now().strftime('%d/%m/%Y a las %H:%M')}")

    # ═══════════════════════════════════════════════════
    # RESUMEN - 4 TARJETAS
    # ═══════════════════════════════════════════════════

    y = height - 170

    p.setFillColor(C_NEGRO)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Resumen general")
    y -= 25

    # 4 tarjetas en fila
    card_width = (width - 120) / 4
    card_height = 70
    card_y = y - card_height

    stats = [
        ('Clases', len(clases_unicas), C_MORADO),
        ('Prácticas', practicas_total, C_CYAN),
        ('Estudiantes', len(estudiantes_unicos), C_VERDE),
        ('Promedio', f"{promedio_global}%", C_VERDE if promedio_global >= 70 else (C_AMARILLO if promedio_global >= 50 else C_ROJO)),
    ]

    for i, (label, value, color) in enumerate(stats):
        x = 50 + i * (card_width + 5)

        # Fondo
        p.setFillColor(C_GRIS_CLARO)
        p.roundRect(x, card_y, card_width, card_height, 6, fill=1, stroke=0)

        # Barra de color superior
        p.setFillColor(color)
        p.roundRect(x, card_y + card_height - 4, card_width, 4, 2, fill=1, stroke=0)

        # Valor
        p.setFillColor(C_NEGRO)
        p.setFont("Helvetica-Bold", 20)
        p.drawString(x + 12, card_y + 35, str(value))

        # Label
        p.setFillColor(C_GRIS)
        p.setFont("Helvetica", 9)
        p.drawString(x + 12, card_y + 15, label.upper())

    y = card_y - 25

    # ═══════════════════════════════════════════════════
    # TOP DEBILIDADES
    # ═══════════════════════════════════════════════════

    if top_debilidades:
        p.setFillColor(C_NEGRO)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "Top debilidades")
        y -= 25

        for i, d in enumerate(top_debilidades, 1):
            if y < 130:
                # Guardar pie de página antes de nueva página
                p.setFillColor(C_GRIS)
                p.setFont("Helvetica-Oblique", 8)
                p.drawString(50, 30, "Reporte generado automáticamente por QBYT · qbyt.app")
                p.showPage()
                y = height - 60

            # Fondo de la tarjeta
            p.setFillColor(C_GRIS_CLARO)
            p.roundRect(45, y - 55, width - 90, 60, 6, fill=1, stroke=0)

            # Color según % error
            if d['porcentaje_error'] >= 70:
                color_nivel = C_ROJO
                color_bg_nivel = C_ROJO_CLARO
            elif d['porcentaje_error'] >= 50:
                color_nivel = C_AMARILLO
                color_bg_nivel = C_AMARILLO_CLARO
            else:
                color_nivel = C_VERDE
                color_bg_nivel = C_VERDE_CLARO

            # Barra izquierda de color
            p.setFillColor(color_nivel)
            p.roundRect(45, y - 55, 5, 60, 2, fill=1, stroke=0)

            # Número en círculo
            p.setFillColor(color_nivel)
            p.circle(75, y - 25, 12, fill=1, stroke=0)
            p.setFillColor(C_BLANCO)
            p.setFont("Helvetica-Bold", 12)
            num_str = str(i)
            p.drawCentredString(75, y - 29, num_str)

            # Nombre
            p.setFillColor(C_NEGRO)
            p.setFont("Helvetica-Bold", 13)
            p.drawString(100, y - 15, d['nombre'])

            # Meta info
            p.setFillColor(C_GRIS)
            p.setFont("Helvetica", 9)
            meta = f"{d['fallos']} errores · {d['aciertos']} aciertos · {d['total']} intentos"
            p.drawString(100, y - 32, meta)

            # Confusiones
            if d['confusiones']:
                conf_str = "Confunden con: " + ", ".join(
                    f"{c['respuesta']} ({c['veces']})" for c in d['confusiones']
                )
                p.setFillColor(C_GRIS)
                p.setFont("Helvetica-Oblique", 8)
                p.drawString(100, y - 47, conf_str[:80])

            # % error en la derecha (con fondo de color)
            pct_text = f"{d['porcentaje_error']}%"
            p.setFillColor(color_bg_nivel)
            p.roundRect(width - 130, y - 35, 80, 28, 6, fill=1, stroke=0)
            p.setFillColor(color_nivel)
            p.setFont("Helvetica-Bold", 14)
            p.drawCentredString(width - 90, y - 25, pct_text)

            y -= 68

        y -= 10

    # ═══════════════════════════════════════════════════
    # DOMINADAS
    # ═══════════════════════════════════════════════════

    if dominadas:
        if y < 180:
            p.setFillColor(C_GRIS)
            p.setFont("Helvetica-Oblique", 8)
            p.drawString(50, 30, "Reporte generado automáticamente por QBYT · qbyt.app")
            p.showPage()
            y = height - 60

        p.setFillColor(C_NEGRO)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "Prácticas dominadas")
        y -= 25

        # Grid de 2 columnas
        col_width = (width - 110) / 2
        for idx, d in enumerate(dominadas):
            col = idx % 2
            row = idx // 2

            x = 50 + col * (col_width + 10)
            item_y = y - row * 50

            # Fondo verde claro
            p.setFillColor(C_VERDE_CLARO)
            p.roundRect(x, item_y - 40, col_width, 45, 6, fill=1, stroke=0)

            # Barra verde izquierda
            p.setFillColor(C_VERDE)
            p.roundRect(x, item_y - 40, 4, 45, 2, fill=1, stroke=0)

            # Check + nombre
            p.setFillColor(C_VERDE_OSCURO)
            p.setFont("Helvetica-Bold", 11)
            p.drawString(x + 15, item_y - 15, f"✓ {d['nombre']}")

            # Meta
            p.setFillColor(C_GRIS)
            p.setFont("Helvetica", 8)
            p.drawString(x + 15, item_y - 32, f"{d['porcentaje_acierto']}% · {d['total']} intentos")

            # % grande a la derecha
            p.setFillColor(C_VERDE)
            p.setFont("Helvetica-Bold", 14)
            p.drawRightString(x + col_width - 15, item_y - 20, f"{d['porcentaje_acierto']}%")

        rows = (len(dominadas) + 1) // 2
        y -= rows * 50 + 15

    # ═══════════════════════════════════════════════════
    # COMPARATIVA POR CLASE
    # ═══════════════════════════════════════════════════

    if comparativa_clases:
        if y < 180:
            p.setFillColor(C_GRIS)
            p.setFont("Helvetica-Oblique", 8)
            p.drawString(50, 30, "Reporte generado automáticamente por QBYT · qbyt.app")
            p.showPage()
            y = height - 60

        p.setFillColor(C_NEGRO)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "Comparativa por clase")
        y -= 25

        for c in comparativa_clases:
            if y < 130:
                p.setFillColor(C_GRIS)
                p.setFont("Helvetica-Oblique", 8)
                p.drawString(50, 30, "Reporte generado automáticamente por QBYT · qbyt.app")
                p.showPage()
                y = height - 60

            # Fondo
            p.setFillColor(C_GRIS_CLARO)
            p.roundRect(45, y - 50, width - 90, 55, 6, fill=1, stroke=0)

            # Color según nivel
            if c['porcentaje'] >= 70:
                color_nivel = C_VERDE
                color_bg_nivel = C_VERDE_CLARO
            elif c['porcentaje'] >= 50:
                color_nivel = C_AMARILLO
                color_bg_nivel = C_AMARILLO_CLARO
            else:
                color_nivel = C_ROJO
                color_bg_nivel = C_ROJO_CLARO

            # Nombre de clase
            p.setFillColor(C_NEGRO)
            p.setFont("Helvetica-Bold", 12)
            p.drawString(60, y - 18, c['clase'].nombre[:45])

            # Info
            p.setFillColor(C_GRIS)
            p.setFont("Helvetica", 9)
            p.drawString(60, y - 35, f"{c['practicas']} prácticas · {c['aciertos']}/{c['total']} aciertos")

            # Barra de progreso visual
            bar_x = 60
            bar_y = y - 48
            bar_w = width - 260
            bar_h = 6

            # Fondo de la barra
            p.setFillColor(C_BLANCO)
            p.roundRect(bar_x, bar_y, bar_w, bar_h, 3, fill=1, stroke=0)

            # Relleno de la barra según %
            p.setFillColor(color_nivel)
            fill_w = (c['porcentaje'] / 100) * bar_w
            if fill_w > 0:
                p.roundRect(bar_x, bar_y, fill_w, bar_h, 3, fill=1, stroke=0)

            # % grande a la derecha
            p.setFillColor(color_bg_nivel)
            p.roundRect(width - 135, y - 33, 85, 30, 6, fill=1, stroke=0)
            p.setFillColor(color_nivel)
            p.setFont("Helvetica-Bold", 14)
            p.drawCentredString(width - 92.5, y - 22, f"{c['porcentaje']}%")

            y -= 60

    # ═══════════════════════════════════════════════════
    # PIE DE PÁGINA
    # ═══════════════════════════════════════════════════

    # Banda inferior
    p.setFillColor(C_VERDE)
    p.rect(0, 0, width, 4, fill=1, stroke=0)

    p.setFillColor(C_GRIS)
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(50, 20, "Reporte generado automáticamente por QBYT · qbyt.app")
    p.drawRightString(width - 50, 20, f"{timezone.now().strftime('%d/%m/%Y')}")

    p.showPage()
    p.save()
    return response

# ============================================================
# MODO LIBRE - PANTALLA DE SELECCIÓN
# ============================================================
@login_required
def practicar(request):
    """Pantalla de selección del modo libre."""
    if request.user.perfil.rol != 'estudiante':
        messages.error(request, 'Solo los estudiantes pueden acceder al modo libre.')
        return redirect('inicio')

    # Estadísticas del estudiante
    practicas = PracticaLibre.objects.filter(estudiante=request.user)

    total_practicas = practicas.count()

    if total_practicas > 0:
        total_aciertos = sum(p.aciertos for p in practicas)
        total_preguntas = sum(p.total_preguntas for p in practicas)
        promedio = round((total_aciertos / total_preguntas) * 100, 1) if total_preguntas > 0 else 0
    else:
        promedio = 0
        total_aciertos = 0
        total_preguntas = 0

    # Últimas 5 prácticas
    ultimas_practicas = practicas.order_by('-fecha')[:5]

    # Estadísticas por tipo
    stats_por_tipo = []
    for tipo_value, tipo_label in PracticaLibre.TIPO_CHOICES:
        tipo_practicas = practicas.filter(tipo_practica=tipo_value)
        if tipo_practicas.exists():
            aciertos = sum(p.aciertos for p in tipo_practicas)
            total = sum(p.total_preguntas for p in tipo_practicas)
            pct = round((aciertos / total) * 100, 1) if total > 0 else 0
            stats_por_tipo.append({
                'tipo': tipo_value,
                'label': tipo_label,
                'practicas': tipo_practicas.count(),
                'porcentaje': pct,
            })

    context = {
        'total_practicas': total_practicas,
        'promedio': promedio,
        'total_aciertos': total_aciertos,
        'total_preguntas': total_preguntas,
        'ultimas_practicas': ultimas_practicas,
        'stats_por_tipo': stats_por_tipo,
        'tipos_disponibles': PracticaLibre.TIPO_CHOICES,
    }

    return render(request, 'ejercicios/practicar.html', context)


# ============================================================
# MODO LIBRE - SESIÓN DE PRÁCTICA
# ============================================================
@login_required
def practicar_sesion(request):
    """Sesión de práctica libre con la configuración elegida."""
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    tipo = request.GET.get('tipo', 'intervalos')
    dificultad = request.GET.get('dificultad', 'medio')
    num_preguntas = int(request.GET.get('preguntas', 10))
    instrumento = request.GET.get('instrumento', 'piano')

    # Limitar entre 3 y 30
    num_preguntas = max(3, min(30, num_preguntas))

    config = {
        'tipo_practica': tipo,
        'dificultad': dificultad,
        'num_preguntas': num_preguntas,
        'instrumento': instrumento,
    }

    context = {
        'config': config,
        'config_json': json.dumps(config),
    }

    return render(request, 'ejercicios/practicar_sesion.html', context)


# ============================================================
# MODO LIBRE - GUARDAR RESULTADO
# ============================================================
@login_required
@require_POST
def guardar_practica_libre(request):
    """Guarda el resultado de una sesión de modo libre."""
    try:
        data = json.loads(request.body)

        tipo = data.get('tipo', 'intervalos')
        dificultad = data.get('dificultad', 'medio')
        instrumento = data.get('instrumento', 'piano')
        aciertos = int(data.get('aciertos', 0))
        total = int(data.get('total', 0))
        detalle = data.get('detalle', [])

        practica = PracticaLibre.objects.create(
            estudiante=request.user,
            tipo_practica=tipo,
            dificultad=dificultad,
            instrumento=instrumento,
            aciertos=aciertos,
            total_preguntas=total,
            detalle_respuestas=detalle,
        )

        return JsonResponse({
            'success': True,
            'practica_id': practica.id,
            'porcentaje': practica.porcentaje,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def crear_entrenamiento_avanzado(request, clase_id, subtipo):
    """
    Crea un ejercicio de entrenamiento avanzado.
    subtipo: 'oido_absoluto' | 'oido_relativo' | 'tapping_ritmico' | 'dictado_melodico'
    """
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)

    SUBTIPOS_VALIDOS = ['oido_absoluto', 'oido_relativo', 'tapping_ritmico', 'dictado_melodico']
    if subtipo not in SUBTIPOS_VALIDOS:
        messages.error(request, 'Tipo de entrenamiento no válido.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    SUBTIPO_LABELS = {
        'oido_absoluto': 'Oído Absoluto',
        'oido_relativo': 'Oído Relativo',
        'tapping_ritmico': 'Tapping Rítmico',
        'dictado_melodico': 'Dictado Melódico',
    }

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite = request.POST.get('fecha_limite')
        dificultad = request.POST.get('dificultad', 'medio')
        num_preguntas = int(request.POST.get('num_preguntas', 10))
        instrumento = request.POST.get('instrumento', 'piano')

        # Validaciones
        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect('ejercicios:crear_entrenamiento_avanzado', clase_id=clase.id, subtipo=subtipo)

        if not fecha_limite:
            messages.error(request, 'La fecha límite es obligatoria.')
            return redirect('ejercicios:crear_entrenamiento_avanzado', clase_id=clase.id, subtipo=subtipo)

        try:
            fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('ejercicios:crear_entrenamiento_avanzado', clase_id=clase.id, subtipo=subtipo)

        # Config específica por subtipo
        config = {
            'subtipo_avanzado': subtipo,
            'dificultad': dificultad,
            'num_preguntas': num_preguntas,
            'instrumento': instrumento,
        }

        # Extras según el subtipo
        if subtipo == 'oido_absoluto':
            config['rango_notas'] = request.POST.get('rango_notas', 'basico')

        elif subtipo == 'oido_relativo':
            config['tonalidad_base'] = request.POST.get('tonalidad_base', 'C')
            config['rango_notas'] = request.POST.get('rango_notas', 'basico')

        elif subtipo == 'tapping_ritmico':
            config['bpm'] = int(request.POST.get('bpm', 60))
            config['tolerancia_ms'] = int(request.POST.get('tolerancia_ms', 150))

        elif subtipo == 'dictado_melodico':
            config['tonalidad'] = request.POST.get('tonalidad', 'C')
            config['notas_min'] = int(request.POST.get('notas_min', 3))
            config['notas_max'] = int(request.POST.get('notas_max', 5))

        # Crear el ejercicio
        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='entrenamiento_avanzado',
            fecha_limite=fecha_limite_dt,
            config_auditivo=config,
        )

        # Recursos
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(
            request,
            f'Entrenamiento "{titulo}" ({SUBTIPO_LABELS[subtipo]}) creado correctamente.'
        )
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_entrenamiento_avanzado.html', {
        'clase': clase,
        'subtipo': subtipo,
        'subtipo_label': SUBTIPO_LABELS[subtipo],
        'recursos_disponibles': recursos_disponibles,
    })

@login_required
def resolver_entrenamiento_avanzado(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(
        Ejercicio, id=ejercicio_id, clase=clase, tipo='entrenamiento_avanzado'
    )

    return render(request, 'ejercicios/resolver_entrenamiento_avanzado.html', {
        'ejercicio': ejercicio,
        'clase': clase,
    })

@login_required
@require_POST
def guardar_practica_avanzada(request, ejercicio_id):
    """
    Guarda el resultado de una práctica de entrenamiento avanzado.
    Tipos soportados: oido_absoluto, oido_relativo, tapping_ritmico, dictado_melodico.
    """
    import logging
    logger = logging.getLogger(__name__)

    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)

    if ejercicio.tipo != 'entrenamiento_avanzado':
        return JsonResponse({'error': 'Tipo de ejercicio inválido'}, status=400)

    # ═══════════════════════════════════════════════════
    # VALIDAR QUE EL ESTUDIANTE ESTÉ INSCRITO EN LA CLASE
    # ═══════════════════════════════════════════════════
    if request.user not in ejercicio.clase.estudiantes.all():
        return JsonResponse({'error': 'No estás inscrito en esta clase'}, status=403)

    # ═══════════════════════════════════════════════════
    # PARSEAR DATOS
    # ═══════════════════════════════════════════════════
    try:
        aciertos = int(request.POST.get('aciertos', 0))
        total = int(request.POST.get('total', 0))
        detalle_raw = request.POST.get('detalle', '[]')
        detalle = json.loads(detalle_raw) if detalle_raw else []
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f'Error parseando datos: {e}')
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)

    if total <= 0:
        return JsonResponse({'error': 'El total de preguntas debe ser mayor a 0'}, status=400)

    # ═══════════════════════════════════════════════════
    # CALCULAR CALIFICACIÓN (100% → 5.0, 0% → 1.0)
    # ═══════════════════════════════════════════════════
    porcentaje = (aciertos / total) * 100
    nota = round(Decimal(porcentaje) / Decimal(20), 1)
    nota = max(Decimal('1.0'), min(Decimal('5.0'), nota))

    aprobado = nota >= Decimal('3.0')

    # ═══════════════════════════════════════════════════
    # CREAR EL INTENTO
    # ═══════════════════════════════════════════════════
    try:
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio,
            calificacion=nota,
            aprobado=aprobado,
        )
    except Exception as e:
        logger.error(f'Error creando IntentoEjercicio: {e}')
        return JsonResponse({'error': f'Error al guardar intento: {e}'}, status=500)

    # ═══════════════════════════════════════════════════
    # GUARDAR DETALLE EN PracticaAuditiva
    # ═══════════════════════════════════════════════════
    subtipo = ejercicio.config_auditivo.get('subtipo_avanzado', 'oido_absoluto')

    # Validar que el subtipo esté en los TIPO_CHOICES del modelo
    TIPOS_VALIDOS = [choice[0] for choice in PracticaAuditiva.TIPO_CHOICES]
    if subtipo not in TIPOS_VALIDOS:
        logger.warning(
            f'Subtipo "{subtipo}" no válido para PracticaAuditiva. '
            f'Tipos válidos: {TIPOS_VALIDOS}'
        )
        subtipo = 'oido_absoluto'  # fallback

    try:
        PracticaAuditiva.objects.create(
            intento=intento,
            tipo_practica=subtipo,
            aciertos=aciertos,
            total_preguntas=total,
            detalle_respuestas=detalle,
        )
    except Exception as e:
        # No rompemos la respuesta si falla el detalle; el intento ya está guardado
        logger.warning(f'Error guardando PracticaAuditiva: {e}')

    # ═══════════════════════════════════════════════════
    # NOTIFICAR AL ESTUDIANTE (opcional)
    # ═══════════════════════════════════════════════════
    try:
        from notificaciones.services import crear_notificacion
        crear_notificacion(
            usuario=request.user,
            tipo='sistema',
            titulo='✅ Práctica avanzada completada',
            mensaje=f'Terminaste "{ejercicio.titulo}" con {aciertos}/{total} aciertos.',
            url_destino=f'/estudiante/clase/{ejercicio.clase.id}/',
        )
    except Exception as e:
        logger.warning(f'No se pudo enviar notificación: {e}')

    # ═══════════════════════════════════════════════════
    # RESPUESTA FINAL
    # ═══════════════════════════════════════════════════
    return JsonResponse({
        'success': True,
        'nota': float(nota),
        'aprobado': aprobado,
        'aciertos': aciertos,
        'total': total,
        'porcentaje': round(porcentaje, 1),
    })