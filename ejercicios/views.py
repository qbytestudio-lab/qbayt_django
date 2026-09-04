from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from datetime import datetime
from django.utils import timezone  #  NUEVO
from .models import (Ejercicio, Pregunta, Opcion, IntentoEjercicio, RespuestaEstudiante,)
from clase.models import Clase
from notificaciones.services import notificar_nuevo_ejercicio, notificar_calificacion

# ============================================================
# VISTA GENERAL / ENRUTADOR PARA CREAR EJERCICIO
# ============================================================
@login_required
def crear_ejercicio(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    # Si mandan el tipo por parámetro GET (ej: ?tipo=juego), redirigimos a su vista correspondiente
    tipo = request.GET.get('tipo', 'quiz')
    
    if tipo == 'quiz':
        return redirect('ejercicios:crear_quiz', clase_id=clase.id)
    elif tipo == 'imagen_quiz':
        return redirect('ejercicios:crear_imagen_quiz', clase_id=clase.id)
    elif tipo == 'juego':
        return redirect('ejercicios:crear_juego', clase_id=clase.id)
    elif tipo == 'texto':
        return redirect('ejercicios:crear_texto', clase_id=clase.id)
    elif tipo == 'verdadero_falso':
        return redirect('ejercicios:crear_verdadero_falso', clase_id=clase.id)
    elif tipo == 'completar':
        return redirect('ejercicios:crear_completar', clase_id=clase.id)
        
    # Si entra por primera vez sin tipo o elijas la opción por defecto:
    return render(request, 'ejercicios/crear_quiz.html', {'clase': clase})
# ============================================================
# CREAR QUIZ
# ============================================================
@login_required
def crear_quiz(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        fecha_limite = request.POST.get('fecha_limite') or None
        
        ejercicio = Ejercicio.objects.create(
            clase=clase,
            tipo='quiz',
            titulo=titulo,
            descripcion=descripcion,
            fecha_limite=fecha_limite
        )
        
        i = 1
        while f'pregunta_{i}' in request.POST:
            enunciado_pregunta = request.POST.get(f'pregunta_{i}')
            imagen_pregunta = request.FILES.get(f'imagen_pregunta_{i}')
            
            if enunciado_pregunta:
                pregunta = Pregunta.objects.create(
                    ejercicio=ejercicio,
                    enunciado=enunciado_pregunta,
                    imagen=imagen_pregunta
                )
                
                opcion_correcta_index = request.POST.get(f'correcta_{i}')
                
                for j in range(1, 5):
                    texto_opcion = request.POST.get(f'opcion_{i}_{j}')
                    if texto_opcion:
                        es_correcta = (str(j) == str(opcion_correcta_index))
                        Opcion.objects.create(
                            pregunta=pregunta,
                            texto_opcion=texto_opcion,
                            es_correcta=es_correcta
                        )
            i += 1
        
        # ✅ NOTIFICAR A LOS ESTUDIANTES
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)
        
        messages.success(request, 'Quiz creado correctamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_quiz.html', {'clase': clase})


# ============================================================
# CREAR QUIZ CON VIDEO
# ============================================================
@login_required
def crear_video_quiz(request, clase_id):
    """
    Vista para crear un ejercicio de tipo Video + Quiz
    """
    from django.utils import timezone
    
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite = request.POST.get('fecha_limite')
        video_principal = request.FILES.get('video_principal')
        video_url = request.POST.get('video_url', '').strip()
        imagen_principal = request.FILES.get('imagen_principal')
        
        # Validar título
        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect('ejercicios:crear_video_quiz', clase_id=clase.id)
        
        # Validar fecha límite obligatoria
        if not fecha_limite:
            messages.error(request, 'La fecha límite es obligatoria.')
            return redirect('ejercicios:crear_video_quiz', clase_id=clase.id)
        
        # Convertir fecha límite
        try:
            fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('ejercicios:crear_video_quiz', clase_id=clase.id)
        
        # Validar que la fecha no sea pasada
        ahora = timezone.now()
        if fecha_limite_dt < ahora.replace(tzinfo=None):
            messages.error(request, 'No puedes usar una fecha límite pasada.')
            return redirect('ejercicios:crear_video_quiz', clase_id=clase.id)
        
        # Validar video o URL
        if not video_principal and not video_url:
            messages.error(request, 'Debes subir un video o proporcionar una URL.')
            return redirect('ejercicios:crear_video_quiz', clase_id=clase.id)
        
        # Validar tamaño del video (máx 100MB)
        if video_principal and video_principal.size > 100 * 1024 * 1024:
            messages.error(request, 'El video no debe superar los 100MB.')
            return redirect('ejercicios:crear_video_quiz', clase_id=clase.id)
        
        # Crear el ejercicio
        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='video_quiz',
            fecha_limite=fecha_limite_dt,
            video_principal=video_principal if video_principal else None,
            video_url=video_url if video_url else None,
            imagen_principal=imagen_principal if imagen_principal else None,
        )
        
        # Procesar preguntas
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
            
            if not texto_pregunta:
                continue
            
            # Crear pregunta
            pregunta = Pregunta.objects.create(
                ejercicio=ejercicio,
                enunciado=texto_pregunta,
            )
            
            # Procesar opciones
            correcta = request.POST.get(f'correcta_{i}')
            
            for j in range(1, 5):
                texto_opcion = request.POST.get(f'opcion_{i}_{j}', '').strip()
                
                if not texto_opcion:
                    continue
                
                es_correcta = (str(j) == str(correcta))
                
                # ✅ CORREGIDO: usar texto_opcion en lugar de texto
                Opcion.objects.create(
                    pregunta=pregunta,
                    texto_opcion=texto_opcion,  # ✅ CAMBIADO
                    es_correcta=es_correcta,
                )
        
        # ✅ NOTIFICAR A LOS ESTUDIANTES
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)
        
        messages.success(request, f'Ejercicio "{titulo}" creado correctamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)
    
    context = {
        'clase': clase,
    }
    
    return render(request, 'ejercicios/crear_video_quiz.html', context)

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

        # ✅ NOTIFICAR A LOS ESTUDIANTES
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Juego creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_juego.html', {'clase': clase})


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

        # ✅ NOTIFICAR A LOS ESTUDIANTES
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Texto creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_texto.html', {'clase': clase})


# ============================================================
# CREAR VERDADERO / FALSO
# ============================================================
@login_required
def crear_verdadero_falso(request, clase_id):
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
            tipo='verdadero_falso'
        )

        # ✅ NOTIFICAR A LOS ESTUDIANTES
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Ejercicio V/F creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_verdadero_falso.html', {'clase': clase})


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

        # ✅ NOTIFICAR A LOS ESTUDIANTES
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Ejercicio de completar creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    return render(request, 'ejercicios/crear_completar.html', {'clase': clase})


# ============================================================
# CALIFICAR EJERCICIO
# ============================================================
@login_required
def calificar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)

    respuestas = intento.respuestas.select_related(
        'pregunta',
        'opcion_seleccionada'
    ).all()

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

        ejercicio = intento.ejercicio
        clase = ejercicio.clase
        estudiante = intento.estudiante

        # ✅ NOTIFICAR AL ESTUDIANTE SOBRE SU CALIFICACIÓN
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

        return redirect('ejercicios:detalle_ejercicio_docente', clase_id=clase.id, ejercicio_id=ejercicio.id)

    return render(
        request,
        'ejercicios/calificar_ejercicio.html',
        {
            'intento': intento,
            'respuestas': respuestas,
            'ejercicio': intento.ejercicio,       
            'clase': intento.ejercicio.clase,
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

    return render(
        request,
        'ejercicios/detalle_ejercicio_docente.html',
        {
            'clase': clase,
            'ejercicio': ejercicio,
            'intentos': intentos,
        }
    )


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
    return redirect('clase:detalle_clase', clase_id=clase_id)


@login_required
def reenviar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
    
    clase_id = intento.ejercicio.clase.id
    ejercicio_id = intento.ejercicio.id
    
    intento.respuestas.all().delete()
    intento.delete()
    
    messages.warning(request, "El intento ha sido rechazado. El estudiante ya puede volver a realizar el ejercicio.")
    
    return redirect('ejercicios:detalle_ejercicio_docente', clase_id=clase_id, ejercicio_id=ejercicio_id)