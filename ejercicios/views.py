from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    Ejercicio,
    Pregunta,
    Opcion,
    IntentoEjercicio,
    RespuestaEstudiante,
)
from clase.models import Clase
# ============================================================
# Vista intermedia
# ============================================================
@login_required
def crear_ejercicio(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    return render(
        request,
        'ejercicios/crear_ejercicio.html',
        {'clase': clase}
    )



# ============================================================
# CREAR QUIZ
# ============================================================

@login_required
def crear_quiz(request, clase_id):
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
            tipo='quiz'
        )

        messages.success(
            request,
            'Quiz creado exitosamente.'
        )

        return redirect(
            'detalle_clase',
            clase_id=clase.id
        )

    return render(
        request,
        'ejercicios/crear_quiz.html',
        {'clase': clase}
    )


# ============================================================
# CREAR QUIZ CON IMAGEN
# ============================================================

@login_required
def crear_imagen_quiz(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':

        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        imagen = request.FILES.get('imagen_principal')

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(request.path)

        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            imagen_principal=imagen,
            tipo='imagen_quiz'
        )

        messages.success(
            request,
            'Ejercicio de imagen creado exitosamente.'
        )

        return redirect(
            'detalle_clase',
            clase_id=clase.id
        )

    return render(
        request,
        'ejercicios/crear_imagen_quiz.html',
        {'clase': clase}
    )


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

        messages.success(
            request,
            'Juego creado exitosamente.'
        )

        return redirect(
            'detalle_clase',
            clase_id=clase.id
        )

    return render(
        request,
        'ejercicios/crear_juego.html',
        {'clase': clase}
    )


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

        messages.success(
            request,
            'Texto creado exitosamente.'
        )

        return redirect(
            'detalle_clase',
            clase_id=clase.id
        )

    return render(
        request,
        'ejercicios/crear_texto.html',
        {'clase': clase}
    )


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

        messages.success(
            request,
            'Ejercicio V/F creado exitosamente.'
        )

        return redirect(
            'detalle_clase',
            clase_id=clase.id
        )

    return render(
        request,
        'ejercicios/crear_verdadero_falso.html',
        {'clase': clase}
    )


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

        messages.success(
            request,
            'Ejercicio de completar creado exitosamente.'
        )

        return redirect(
            'detalle_clase',
            clase_id=clase.id
        )

    return render(
        request,
        'ejercicios/crear_completar.html',
        {'clase': clase}
    )


# ============================================================
# CALIFICAR EJERCICIO
# ============================================================

@login_required
def calificar_ejercicio(request, intento_id):

    intento = get_object_or_404(
        IntentoEjercicio,
        id=intento_id
    )

    respuestas = intento.respuestas.select_related(
        'pregunta',
        'opcion_seleccionada'
    ).all()

    if request.method == 'POST':

        nota_str = request.POST.get('calificacion', '').strip()
        retroalimentacion = request.POST.get(
            'retroalimentacion',
            ''
        ).strip()

        if not nota_str:
            messages.error(
                request,
                'Por favor ingresa una calificación.'
            )

            return redirect(request.path)

        try:
            nota = Decimal(nota_str)
        except InvalidOperation:
            messages.error(
                request,
                'La calificación ingresada no es válida.'
            )

            return redirect(request.path)

        if nota < Decimal('1.0') or nota > Decimal('5.0'):
            messages.error(
                request,
                'La calificación debe estar entre 1.0 y 5.0.'
            )

            return redirect(request.path)

        NOTA_MINIMA = Decimal('3.0')

        intento.calificacion = nota
        intento.retroalimentacion = retroalimentacion
        intento.aprobado = nota >= NOTA_MINIMA

        intento.save()

        ejercicio = intento.ejercicio
        clase = ejercicio.clase
        estudiante = intento.estudiante

        total_intentos = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio=ejercicio
        ).count()

        if intento.aprobado:

            messages.success(
                request,
                '¡Calificación guardada correctamente! '
                'El estudiante aprobó.'
            )

        else:

            if total_intentos < 2:

                messages.warning(
                    request,
                    f'Calificación menor a {NOTA_MINIMA}. '
                    'El estudiante puede realizar un segundo '
                    'y último intento.'
                )

            else:

                messages.error(
                    request,
                    f'Calificación menor a {NOTA_MINIMA}. '
                    'El estudiante ha agotado sus 2 intentos '
                    'y ha sido bloqueado de la clase.'
                )

                if estudiante in clase.estudiantes.all():
                    clase.estudiantes.remove(estudiante)

        return redirect(
            'detalle_ejercicio_docente',
            clase_id=clase.id,
            ejercicio_id=ejercicio.id
        )

    return render(
        request,
        'ejercicios/calificar_ejercicio.html',
        {
            'intento': intento,
            'respuestas': respuestas,
        }
    )


#def calificar_ejercicio(request, intento_id):
#    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
#    respuestas = intento.respuestas.all()
#    
#    if request.method == 'POST':
#        nota_str = request.POST.get('calificacion')
#        retro = request.POST.get('retroalimentacion', '')
#        
#        if not nota_str:
#            messages.error(request, "Por favor ingresa una calificación.")
#            return redirect(request.path)

#        nota = float(nota_str)
#        intento.calificacion = nota
#        intento.retroalimentacion = retro
#        intento.save() # Guardamos la calificación en este intento
#        
#        NOTA_MINIMA = 3.0 
#        ejercicio = intento.ejercicio
#        clase = ejercicio.clase
#        estudiante = intento.estudiante
#        clase_id = clase.id
#        ejercicio_id = ejercicio.id

        # Contamos cuántos intentos lleva en total este estudiante
#        total_intentos = IntentoEjercicio.objects.filter(
#            estudiante=estudiante, 
#            ejercicio=ejercicio
#        ).count()

#        if nota >= NOTA_MINIMA:
#            messages.success(request, "¡Calificación guardada correctamente! El estudiante aprobó.")
#        else:
#            if total_intentos < 2:
#                messages.warning(request, f"Calificación menor a {NOTA_MINIMA}. El estudiante puede realizar un segundo y último intento.")
#            else:
#                # 🔴 BLOQUEO DEL CURSO: Si ya cumplió 2 intentos y volvió a reprobar
#                messages.error(request, f"Calificación menor a {NOTA_MINIMA}. El estudiante ha agotado sus 2 intentos y ha sido bloqueado de la clase.")
#                
                # Removemos al estudiante del curso para denegarle el acceso por completo
#                if estudiante in clase.estudiantes.all():
#                    clase.estudiantes.remove(estudiante)
#        
#        return redirect('detalle_ejercicio_docente', clase_id=clase_id, ejercicio_id=ejercicio_id)

#    return render(request, 'ejercicios/calificar_ejercicio.html', {
#        'intento': intento,
#        'respuestas': respuestas
#    })