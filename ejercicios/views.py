from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from clase.models import Clase  # <--- Importamos Clase (con C mayúscula)
from .models import Ejercicio, Pregunta, Opcion

def crear_ejercicio(request, clase_id):
    # 1. Buscamos la clase correspondiente
    clase = get_object_or_404(Clase, id=clase_id)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        
        # 2. Creamos la instancia de Ejercicio SIN guardarla en base de datos aún (commit=False)
        nuevo_ejercicio = Ejercicio(
            titulo=titulo,
            descripcion=descripcion,
            clase=clase  # <--- AQUÍ conectamos el ejercicio a esta clase específica
        )
        nuevo_ejercicio.save() # Ahora sí lo guardamos con su relación creada
        
        # ... Aquí continúa tu código de procesar preguntas/opciones en el POST ...
        
        # Al terminar de procesar todo, redirigimos al detalle de la clase
        messages.success(request, "¡Ejercicio creado con éxito!")
        return redirect('detalle_clase', clase_id=clase.id)
        
    return render(request, 'ejercicios/crear_ejercicio.html', {'clase': clase})
    # VISTA PARA ELIMINAR UN EJERCICIO
def eliminar_ejercicio(request, clase_id, ejercicio_id):
    # Buscamos el ejercicio asegurando que pertenezca a la clase correcta
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase_id=clase_id)
    
    if request.method == 'POST':
        ejercicio.delete()
        messages.success(request, "¡Ejercicio eliminado correctamente!")
        return redirect('detalle_clase', clase_id=clase_id)
        
    # Si entran por GET (por seguridad), también redirigimos
    return redirect('detalle_clase', clase_id=clase_id)


# VISTA PARA EDITAR UN EJERCICIO (Básico: Título y Descripción)
def editar_ejercicio(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        
        if titulo:
            ejercicio.titulo = titulo
            ejercicio.descripcion = descripcion
            ejercicio.save()
            messages.success(request, "¡Ejercicio actualizado con éxito!")
            return redirect('detalle_clase', clase_id=clase.id)
        else:
            messages.error(request, "El título del ejercicio no puede estar vacío.")
            
    return render(request, 'ejercicios/editar_ejercicio.html', {
        'clase': clase,
        'ejercicio': ejercicio
    })