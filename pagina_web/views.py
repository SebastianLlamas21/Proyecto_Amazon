from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.generic import View, ListView, CreateView, DeleteView
from pymongo import MongoClient
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from bson import ObjectId
import bcrypt

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
            db = client['Amazonas']  
            collection = db['usuarios']  

            # Buscar el usuario por email
            usuario = collection.find_one({"Email": email})

            if usuario:
                # Verificar que la contraseña también coincida
                if usuario['Password'] == password:
                    # Verificar que el atributo 'Sesion' sea False
                    if usuario.get('Sesion', False) == False:
                        # Cambiar el valor de 'Sesion' a True
                        collection.update_one({"_id": usuario['_id']}, {"$set": {"Sesion": True}})

                        # Contraseña correcta y sesión iniciada
                        messages.success(request, "Inicio de sesión exitoso")
                        return redirect('sesion_iniciada')  # Redirige a la página 'index_sesion_iniciada'
                    else:
                        messages.error(request, "La sesión ya está iniciada")
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

#Vista Pago
def sesion_iniciada(request):
	return render(request, "index_sesion_iniciada.html") 

#Registro
def registro(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        # Validar que las contraseñas coinciden
        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden")
            return redirect('registro')
        try:
            # Verificar si el correo ya está registrado
            client = MongoClient('mongodb://localhost:27017/')
            db = client['Amazonas']
            usuarios = db['usuarios']
            
            existing_user = usuarios.find_one({"Email": email})
            if existing_user:
                messages.error(request, "Este correo ya está registrado")
                return redirect('registro')
            
            # Hash de la contraseña para seguridad
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Insertar el nuevo usuario en la base de datos
            usuarios.insert_one({
                'Name': name,
                'Email': email,
                'Password': password,
                'Sesion': False
            })
            print({
                'nombre': name,
                'email': email,
                'password': password
            })

            # Mensaje de éxito
            messages.success(request, "Registro exitoso! Ahora puedes iniciar sesión.")
            return redirect('inicio')
        except ConnectionError as e:
            messages.error(request, "Error al conectar con la base de datos.")
            return redirect('registro')
        
    return render(request, 'registro.html')

#Buscar productos
def buscar_productos(request):
    termino = request.GET.get('q', '')  # Obtener el término de búsqueda desde los parámetros GET
    productos = []

    if termino:  # Verificar que el término no esté vacío
        try:
            # Conectar a la base de datos MongoDB
            client = MongoClient('localhost', 27017)
            database = client['Amazonas']
            collection = database['Productos']

            # Buscar productos cuyo nombre coincida parcialmente (insensible a mayúsculas)
            resultados = collection.find({"name": {"$regex": termino, "$options": "i"}})

            # Convertir los resultados a una lista de diccionarios
            productos = [
                {"name": producto["name"], "price": producto["price"], "images": producto["images"]}
                for producto in resultados
            ]

            client.close()  # Cerrar conexión con la base de datos
        except Exception as ex:
            # Si ocurre un error, puedes agregar manejo de errores aquí
            print(f"Error al buscar productos: {ex}")

    # Renderizar los resultados en el template
    return render(request, 'busqueda.html', {"productos": productos, "termino": termino})