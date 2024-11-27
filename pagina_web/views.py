from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.generic import View, ListView, CreateView, DeleteView
from pymongo import MongoClient
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages

#Vista Index

def index(request):
    productos = []  # Lista para almacenar los productos

    try:
        # Conexión a la base de datos MongoDB
        client = MongoClient('localhost', 27017)
        database = client['Amazonas']
        collection = database['Productos']

        # Consulta a MongoDB para obtener los productos
        documentos = collection.find({}, {"name": 1, "price": 1, "images": 1, "_id": 0})

        # Procesar los documentos y agregarlos a la lista de productos
        for documento in documentos:
            productos.append({
                "name": documento.get("name", "Sin nombre"),
                "price": documento.get("price", "Sin precio"),
                "images": documento.get("images", [])
            })
        
    except Exception as ex:
        print("Error durante la conexión: {}".format(ex))
    finally:
        client.close()
        print("Conexión finalizada")
    
    # Pasar los productos al template
    return render(request, 'index.html', {"productos": productos})


# Vista "Carrito"
def carrito(request):
	return render(request, "carrito.html")  


# Vista Inicio
def inicio(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        try:
            # Conexión a MongoDB
            client = MongoClient('localhost', 27017)
            db = client['Amazonas']  # Asegúrate de que tu base de datos se llama 'Amazonas'
            collection = db['Usuarios']  # Asegúrate de que la colección se llama 'Usuarios'

            # Buscar el usuario por email
            usuario = collection.find_one({"Email": email})

            if usuario:
                # Verificar que la contraseña también coincida
                if usuario['Password'] == password:
                    # Contraseña correcta
                    messages.success(request, "Inicio de sesión exitoso")
                    return redirect('index')  # Redirige al inicio si el login es exitoso
                else:
                    # Contraseña incorrecta
                    messages.error(request, "Contraseña incorrecta")
            else:
                # Usuario no encontrado
                messages.error(request, "Correo no registrado")
            
        except Exception as e:
            messages.error(request, f"Error de conexión a la base de datos: {e}")
        
        finally:
            client.close()

    return render(request, 'inicio.html')


#Vista Pago
def pago(request):
	return render(request, "pago.html") 


#Registro
def registro(request):
	return render(request, "registro.html") 