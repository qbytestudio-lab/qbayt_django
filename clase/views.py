from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from .models import Clase, SolicitudClase, Anuncio, InscripcionClase, HistorialInscripcion

def index(request):
    return render(request, 'clase/index.html')
# ═══════════════════════════════════════════
#         GESTIÓN DE CLASES
# ═══════════════════════════════════════════

@login_required
def crear_clase(request):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')

    if request.method == 'POST':
        from datetime import datetime, date
        from django.core.exceptions import ValidationError
        
        nombre = request.POST.get('nombre', '').strip()
        categoria_tema = request.POST.get('categoria_tema')
        descripcion = request.POST.get('descripcion', '').strip()
        imagen = request.FILES.get('imagen')
        max_estudiantes = request.POST.get('max_estudiantes', 35)
        fecha_inicio = request.POST.get('fecha_inicio') or None
        fecha_fin = request.POST.get('fecha_fin') or None
        nivel_previo_id = request.POST.get('nivel_previo')

        nivel_previo = None
        if nivel_previo_id:
            nivel_previo = Clase.objects.filter(id=nivel_previo_id).first()

        #  Validar límite de 3 clases por docente
        clases_docente_count = Clase.objects.filter(docente=request.user).count()
        if clases_docente_count >= 3:
            messages.error(request, 'Has alcanzado el máximo de 3 clases permitidas.')
            return redirect('mis_clases')
        
        # Validaciones de fechas
        hoy = date.today()
        
        # Validar nombre
        if not nombre:
            messages.error(request, 'El nombre de la clase es obligatorio.')
            return redirect('mis_clases')
        
        # Validar categoría
        if not categoria_tema:
            messages.error(request, 'La categoría del tema es obligatoria.')
            return redirect('mis_clases')
        
        # Validar fechas obligatorias
        if not fecha_inicio:
            messages.error(request, 'La fecha de inicio es obligatoria.')
            return redirect('mis_clases')
        
        if not fecha_fin:
            messages.error(request, 'La fecha de finalización es obligatoria.')
            return redirect('mis_clases')
        
        # Convertir strings a objetos date
        try:
            fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('mis_clases')
        
        # Validar que fecha de inicio no sea pasada
        if fecha_inicio_date < hoy:
            messages.error(request, 'No puedes usar una fecha de inicio pasada.')
            return redirect('mis_clases')
        
        # Validar que fecha de fin no sea pasada
        if fecha_fin_date < hoy:
            messages.error(request, 'No puedes usar una fecha de finalización pasada.')
            return redirect('mis_clases')
        
        # Validar que fecha fin sea posterior a inicio
        if fecha_fin_date <= fecha_inicio_date:
            messages.error(request, 'La fecha de finalización debe ser posterior a la fecha de inicio.')
            return redirect('mis_clases')
        
        # Validar mínimo 5 días de duración
        diferencia_dias = (fecha_fin_date - fecha_inicio_date).days
        if diferencia_dias < 5:
            messages.error(
                request, 
                f'La clase debe durar al menos 5 días. Actual: {diferencia_dias} día{"s" if diferencia_dias != 1 else ""}.'
            )
            return redirect('mis_clases')
        
        try:
            # Crear la clase
            clase = Clase(
                nombre=nombre,
                categoria_tema=categoria_tema,
                descripcion=descripcion,
                docente=request.user,
                imagen=imagen,
                max_estudiantes=max_estudiantes if max_estudiantes else 35,
                fecha_inicio=fecha_inicio_date,
                fecha_fin=fecha_fin_date,
                nivel_previo=nivel_previo,
            )
            
            #  Llamar a full_clean() que ejecuta el método clean() del modelo
            # Esto valida el límite de 3 clases por docente
            clase.full_clean()
            
            # Si pasa la validación, guardar
            clase.save()
            messages.success(request, f'Clase "{clase.nombre}" creada exitosamente.')
            
        except ValidationError as e:
            # Mostrar errores de validación del modelo
            if hasattr(e, 'message_dict'):
                for field, errors in e.message_dict.items():
                    messages.error(request, f'{errors[0]}')
                    break
            else:
                # Para errores no relacionados a campos específicos
                if hasattr(e, 'messages'):
                    messages.error(request, e.messages[0])
                else:
                    messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al crear la clase: {str(e)}')

    return redirect('mis_clases')


@login_required
def editar_clase(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        imagen = request.FILES.get('imagen')
        
        if nombre:
            clase.nombre = nombre
            clase.descripcion = descripcion
            if imagen:
                clase.imagen = imagen
            clase.save()
            messages.success(request, "¡Clase actualizada correctamente!")
            return redirect('detalle_clase', clase_id=clase.id)
        else:
            messages.error(request, "El nombre de la clase no puede estar vacío.")
    
    return redirect('detalle_clase', clase_id=clase.id)


@login_required
def eliminar_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        clase.delete()
        messages.success(request, "La clase fue eliminada para siempre.")
        return redirect('mis_clases')
    
    return redirect('detalle_clase', clase_id=clase.id)


@login_required
def detalle_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    
    # Verificar que la clase pertenece al docente
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    # Obtener solicitudes pendientes
    solicitudes = clase.solicitudes.filter(estado='pendiente')
    
    # Obtener anuncios ordenados por fecha
    anuncios = clase.anuncios.all().order_by('-fecha')
    
    # Obtener ejercicios - Verificar la relación correcta
    # Si tu modelo Clase tiene related_name='ejercicios' en la FK de Ejercicio
    ejercicios = clase.ejercicios.all().order_by('-fecha_creacion')
    
    # O si Ejercicio tiene FK a Clase sin related_name específico:
    # from ejercicios.models import Ejercicio
    # ejercicios = Ejercicio.objects.filter(clase=clase).order_by('-fecha_creacion')
    
    # Debug para verificar
    print(f"Clase: {clase.nombre}")
    print(f"Solicitudes: {solicitudes.count()}")
    print(f"Anuncios: {anuncios.count()}")
    print(f"Ejercicios: {ejercicios.count()}")
    
    return render(request, 'clase/detalle_clase.html', {
        'clase': clase,
        'solicitudes': solicitudes,
        'solicitudes_pendientes': solicitudes,
        'anuncios': anuncios,
        'ejercicios': ejercicios,
    })
    
