from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from web.models import Perfil
from django.contrib.auth.decorators import login_required
from docente.models import Clase, SolicitudClase
from .models import Curso

def index(request):
    return render(request, 'web/index.html')

@login_required
def inicio(request):
    # Traemos todos los cursos de la base de datos
    cursos = Curso.objects.all()
    
    # También puedes separarlos por categoría desde aquí si lo prefieres:
    cursos_teoria = Curso.objects.filter(categoria='teoria')
    cursos_auditivo = Curso.objects.filter(categoria='auditivo')
    cursos_instrumento = Curso.objects.filter(categoria='instrumento')

    context = {
        'cursos_teoria': cursos_teoria,
        'cursos_auditivo': cursos_auditivo,
        'cursos_instrumento': cursos_instrumento,
    }
    return render(request, 'web/inicio.html', context)


@login_required
def perfil_administrador(request):
    if request.user.perfil.rol != 'administrador':
        return redirect('inicio')
    return render(request, 'perfil_admin.html')

def registro(request):
    if request.method == 'POST':
        first_name = request.POST ['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        rol = request.POST['rol']

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('registro')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El usuario ya existe.')
            return redirect('registro')

        user = User.objects.create_user(username=username, email=email, password=password1, first_name=first_name,
    last_name=last_name)
        user.save()
        Perfil.objects.create(user=user, rol=rol)
        messages.success(request, '¡Cuenta creada! Inicia sesión.')
        return redirect('login')

    return render(request, 'web/registro.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('inicio')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return redirect('login')

    return render(request, 'web/login.html')

def logout_view(request):
    logout(request)
    return redirect('index')
# Al final de web/views.py

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        usuario = request.user
        # Capturamos los datos que el usuario edite en el formulario
        usuario.username = request.POST.get('username')
        usuario.email = request.POST.get('email')
        usuario.first_name = request.POST.get('first_name')
        usuario.last_name = request.POST.get('last_name')
        usuario.save() # Se guarda directo en MySQL
        
        messages.success(request, '¡Tu perfil ha sido actualizado correctamente!')
        return redirect('inicio')
        
    return redirect('inicio')

@login_required
def eliminar_perfil(request):
    usuario = request.user
    logout(request) # Cerramos la sesión antes de borrarlo para que Django no se enrede
    usuario.delete() # Al borrar el User, el CASCADE borra también su Perfil automáticamente
    messages.success(request, 'Tu cuenta ha sido eliminada permanentemente.')
    return redirect('index')

def cursos(request):
    return render(request, 'clase/cursos.html')

def mis_clases(request):
    return render(request, 'web/mis_clases.html')

def progreso(request):
    return render(request, 'web/progreso.html')

def certificados(request):
    return render(request, 'web/certificados.html')

@login_required
def mis_clases(request):
    clases = request.user.clases_estudiante.all()
    return render(request, 'web/mis_clases.html', {'clases': clases})