from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, authenticate

# 1. Login exclusivo para Admin
def login_admin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff: 
            login(request, user)
            return redirect('panel_admin')
        else:
            messages.error(request, 'Acceso denegado. Credenciales incorrectas o no tienes permisos de administrador.')
            
    return render(request, 'administrador/login_admin.html')

# 2. Panel de Administrador
@login_required
def panel_admin(request):
    if not request.user.is_staff:
        return redirect('inicio') 

    # Traemos a TODOS los usuarios de la base de datos
    todos_los_usuarios = User.objects.all()
    
    # Filtramos en Python (así no falla si el rol no existe o está mal escrito)
    docentes = []
    estudiantes = []
    
    for u in todos_los_usuarios:
        # Si el usuario tiene perfil y el rol es docente
        if hasattr(u, 'perfil') and u.perfil.rol and 'docente' in u.perfil.rol.lower():
            docentes.append(u)
        # Si el usuario tiene perfil y el rol es estudiante
        elif hasattr(u, 'perfil') and u.perfil.rol and 'estudiante' in u.perfil.rol.lower():
            estudiantes.append(u)
        # Si no tiene perfil, lo mandamos a estudiantes por defecto para que no se pierda
        else:
            estudiantes.append(u)

    return render(request, 'administrador/panel_admin.html', {
        'docentes': docentes,
        'estudiantes': estudiantes
    })

# 3. Suspender / Activar
@login_required
def suspender_usuario(request, user_id):
    if not request.user.is_staff:
        return redirect('inicio')
    
    usuario = get_object_or_404(User, id=user_id)
    usuario.is_active = not usuario.is_active # Cambia el estado
    usuario.save()
    
    estado = "activado" if usuario.is_active else "suspendido"
    messages.success(request, f'El usuario {usuario.username} ha sido {estado}.')
    return redirect('panel_admin')

# 4. Eliminar
@login_required
def eliminar_usuario(request, user_id):
    if not request.user.is_staff:
        return redirect('inicio')
    
    usuario = get_object_or_404(User, id=user_id)
    nombre = usuario.username
    usuario.delete()
    messages.success(request, f'El usuario {nombre} ha sido eliminado.')
    return redirect('panel_admin')