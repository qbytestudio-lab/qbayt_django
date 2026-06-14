from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from docente.models import Clase, SolicitudClase

@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clases = request.user.clases_estudiante.all()
    solicitudes = SolicitudClase.objects.filter(estudiante=request.user)
    return render(request, 'perfil_estudiante.html', {
        'clases': clases,
        'solicitudes': solicitudes,
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
        except Clase.DoesNotExist:
            messages.error(request, 'Código inválido.')
    return redirect('perfil_estudiante')

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
    return redirect('perfil_estudiante')

@login_required
def salir_clase(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id)
    clase.estudiantes.remove(request.user)
    messages.success(request, f'Saliste de "{clase.nombre}".')
    return redirect('perfil_estudiante')

@login_required
def explorar_clases(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clases = Clase.objects.exclude(estudiantes=request.user)
    solicitudes_enviadas = SolicitudClase.objects.filter(
        estudiante=request.user
    ).values_list('clase_id', flat=True)
    return render(request, 'explorar_clases.html', {
        'clases': clases,
        'solicitudes_enviadas': solicitudes_enviadas,
    })

@login_required
def detalle_clase_estudiante(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, estudiantes=request.user)
    return render(request, 'detalle_clase_estudiante.html', {'clase': clase})