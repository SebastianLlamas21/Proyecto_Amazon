from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.generic import View, ListView, CreateView, DeleteView
from pymongo import MongoClient
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from bson import ObjectId
from datetime import datetime, timedelta


client = MongoClient('localhost', 27017)
database = client['Amazonas']

#Vista Index
def index(request):
    productos = []  # Lista para almacenar los productos

    try:
        # Conexión a la base de datos MongoDB
        client = MongoClient('localhost', 27017)
        database = client['Amazonas']
        collection = database['Productos']

        # Consulta a MongoDB para obtener los productos, incluyendo _id
        documentos = collection.find({}, {"name": 1, "price": 1, "images": 1, "_id": 1})

        # Procesar los documentos y cambiar el nombre de `_id` a `id`
        for documento in documentos:
            productos.append({
                "id": str(documento.get("_id")),  # Renombrar _id a id
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


#Inicio de sesion
def inicio(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        try:
            # Conexión a MongoDB
            client = MongoClient('localhost', 27017)
            db = client["Amazonas"]
            collection = db["usuarios"]

            # Buscar el usuario en MongoDB
            usuario_mongo = collection.find_one({"Email": email})

            if usuario_mongo:
                # Verificar si la sesión ya está activa
                if usuario_mongo["Sesion"]:
                    messages.error(request, "Ya tienes una sesión activa.")
                    return redirect("index")

                # Autenticar con el sistema de Django
                user_django = authenticate(request, username=usuario_mongo["Name"], password=password)

                if user_django:
                    # Cambiar el estado de sesión en MongoDB a True
                    collection.update_one({"Email": email}, {"$set": {"Sesion": True}})
                    
                    # Iniciar sesión en Django
                    login(request, user_django)
                    messages.success(request, "Inicio de sesión exitoso.")
                    return redirect("index")
                else:
                    messages.error(request, "Credenciales inválidas.")
            else:
                messages.error(request, "Correo no registrado.")

        except Exception as e:
            messages.error(request, f"Error al conectar con la base de datos: {e}")

        finally:
            client.close()

    return render(request, "inicio.html")

#Vista de logout
def logout_view(request):
    """Cerrar la sesión del usuario."""
    if request.user.is_authenticated:
        try:
            # Conexión a MongoDB
            client = MongoClient('localhost', 27017)
            db = client['Amazonas']  # Nombre de la base de datos
            collection = db['usuarios']  # Colección de usuarios

            # Actualizar el estado de sesión en MongoDB
            collection.update_one(
                {"Email": request.user.email},  # Suponiendo que el email identifica al usuario
                {"$set": {"Sesion": False}}
            )
        except Exception as e:
            print(f"Error al actualizar el estado de sesión en MongoDB: {e}")
        finally:
            client.close()
        
        # Cerrar sesión en Django
        logout(request)

    # Redirigir a la página de inicio u otra página
    return redirect('index')


#Registro
def registro(request):
    if request.method == "POST":
        nombre = request.POST["name"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect("registro")

        try:
            registrar_usuario_en_mongo_y_django(nombre, email, password)
            messages.success(request, "Registro exitoso.")
            return redirect("inicio")
        except Exception as e:
            messages.error(request, f"Error al registrar el usuario: {e}")
            return redirect("registro")

    return render(request, "registro.html")

def registrar_usuario_en_mongo_y_django(nombre, email, password):
    """
    Registra un usuario tanto en MongoDB como en Django.
    """
    try:
        # Registrar en MongoDB
        client = MongoClient('localhost', 27017)
        db = client['Amazonas']
        collection = db['usuarios']

        # Insertar el usuario en MongoDB
        mongo_usuario = {
            "Name": nombre,
            "Email": email,
            "Password": make_password(password),  # Cifrado compatible con Django
            "Sesion": False
        }
        collection.insert_one(mongo_usuario)

        # Registrar en Django
        if not User.objects.filter(email=email).exists():
            User.objects.create_user(
                username=nombre,
                email=email,
                password=password  # Django también manejará el cifrado
            )
            print("Usuario registrado en MongoDB y Django.")

        else:
            print("El usuario ya existe en Django. Registro omitido.")
    except Exception as e:
        print(f"Error al registrar usuario: {e}")
    finally:
        client.close()



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


#Vista de carrito
@login_required
def carrito(request):
    productos = []  # Lista para almacenar los productos del carrito
    subtotal = 0

    if request.user.is_authenticated:
        try:
            # Conectar a MongoDB
            client = MongoClient('localhost', 27017)
            db = client["Amazonas"]
            carritos_collection = db["Carritos"]

            # Obtener el carrito del usuario sin convertir el ID a ObjectId
            carrito = carritos_collection.find_one({"user_id": str(request.user.id)})

            if carrito:
                # Procesar los productos del carrito
                for item in carrito.get("productos", []):
                    productos.append({
                        "producto_id": str(item["producto_id"]),  # Convertir el ObjectId a string si es necesario
                        "name": item["name"],
                        "price": item["price"],
                        "cantidad": item["cantidad"],
                        "images": item.get("images", [])
                    })
                    # Calcular el subtotal
                    subtotal += item.get("price", 0) * item.get("cantidad", 1)

            #else:
                #messages.info(request, "Tu carrito está vacío.")
        except Exception as e:
            messages.error(request, f"Error al cargar el carrito: {e}")
        finally:
            client.close()
    else:
        messages.error(request, "Debes iniciar sesión para ver tu carrito.")
        return redirect("inicio")

    if subtotal < 15:
        costo_envio = 10.00  # Envío de $10 para compras menores a $15
        envio_texto = "Envío: $10.00"
    else:
        costo_envio = 0.00  # Envío gratis para compras de $15 o más
        envio_texto = "Envío: Gratis"

    # Calcular el total
    total = subtotal + costo_envio

    return render(request, "carrito.html", {
        "productos": productos,
        "subtotal": subtotal,
        "total": total,
        "costo_envio": costo_envio,
        "envio_texto": envio_texto
    })


#Vista para agregar productos al carrito
def agregar_al_carrito(request):
    if request.method == "POST":
        producto_id = request.POST.get("producto_id")
        cantidad = int(request.POST.get("cantidad", 1))  # Por defecto 1 si no se envía cantidad

        if producto_id and request.user.is_authenticated:
            try:
                # Conectar a MongoDB
                client = MongoClient('localhost', 27017)
                db = client["Amazonas"]
                productos_collection = db["Productos"]
                carritos_collection = db["Carritos"]

                # Usar el ID del usuario como cadena (no convertir a ObjectId)
                usuario_id = str(request.user.id)

                # Buscar el producto
                producto = productos_collection.find_one({"_id": ObjectId(producto_id)})

                if producto:
                    # Buscar el carrito del usuario
                    carrito = carritos_collection.find_one({"user_id": usuario_id})

                    if not carrito:
                        # Crear un nuevo carrito si no existe
                        carrito = {
                            "user_id": usuario_id,  # Guardar el user_id como cadena
                            "productos": []
                        }
                        carritos_collection.insert_one(carrito)

                    # Verificar si el producto ya está en el carrito
                    producto_en_carrito = next(
                        (p for p in carrito["productos"] if str(p["producto_id"]) == producto_id),
                        None
                    )

                    if producto_en_carrito:
                        # Incrementar la cantidad si ya existe
                        producto_en_carrito["cantidad"] += cantidad
                    else:
                        # Agregar un nuevo producto al carrito
                        carrito["productos"].append({
                            "producto_id": producto["_id"],  # Mantener el ObjectId del producto
                            "name": producto["name"],
                            "price": producto["price"],
                            "cantidad": cantidad,
                            "images": producto.get("images", []) 
                        })

                    # Actualizar el carrito en la base de datos
                    carritos_collection.update_one(
                        {"user_id": usuario_id},
                        {"$set": {"productos": carrito["productos"]}}
                    )

                    messages.success(request, f"{producto['name']} ha sido agregado al carrito.")
                else:
                    messages.error(request, "Producto no encontrado.")
            except Exception as e:
                messages.error(request, f"Error al agregar al carrito: {e}")
            finally:
                client.close()
        else:
            messages.error(request, "No se ha proporcionado un ID de producto válido o no estás autenticado.")
        
    return redirect("index")


#Vista para eliminar productos del carrito
def eliminar_del_carrito(request):
    if request.method == "POST" and request.user.is_authenticated:
        producto_id = request.POST.get("producto_id")

        try:
            client = MongoClient('localhost', 27017)
            db = client["Amazonas"]
            carritos_collection = db["Carritos"]

            # Eliminar el producto del carrito
            carritos_collection.update_one(
                {"user_id": str(request.user.id)},
                {"$pull": {"productos": {"producto_id": ObjectId(producto_id)}}}
            )
            #messages.success(request, "Producto eliminado del carrito.")
        except Exception as e:
            messages.error(request, f"Error al eliminar el producto: {e}")
        finally:
            client.close()

    return redirect("carrito")


#Vista para actulizar cantidad de producto en carrito
def actualizar_carrito(request):
    if request.method == "POST" and request.user.is_authenticated:
        producto_id = request.POST.get("producto_id")
        cantidad = int(request.POST.get("cantidad", 1))

        try:
            client = MongoClient('localhost', 27017)
            db = client["Amazonas"]
            carritos_collection = db["Carritos"]

            # Actualizar la cantidad en el carrito
            carritos_collection.update_one(
                {"user_id": str(request.user.id), "productos.producto_id": ObjectId(producto_id)},
                {"$set": {"productos.$.cantidad": cantidad}}
            )
            #messages.success(request, "Cantidad actualizada.")
        except Exception as e:
            messages.error(request, f"Error al actualizar el carrito: {e}")
        finally:
            client.close()

    return redirect("carrito")



#Vista Pago
def pago(request):
    total = request.GET.get('total', 0)  # Recibir el valor total desde el carrito (GET)
    
    try:
        total = float(total)  # Convertir a float si es necesario
    except ValueError:
        total = 0.0

    return render(request, "pago.html", {"total_pago": total})


#Vista para procesar el pago


def procesar_pago(request):
    if request.method == 'POST':
        # Obtener el ID del usuario
        user_id = str(request.user.id) if request.user.is_authenticated else None
        nombre_tarjeta = request.POST.get('card_name')
        numero_tarjeta = request.POST.get('card_number')  # Este dato no debe almacenarse en texto claro, solo para validaciones
        monto = float(request.POST.get('monto', 0))
        metodo_pago = "Tarjeta"  # Por ejemplo, puedes cambiarlo por otros métodos (ej: PayPal, transferencia)

        try:
            # Conectar a MongoDB
            client = MongoClient('localhost', 27017)
            db = client["Amazonas"]
            carritos_collection = db["Carritos"]
            pagos_collection = db["Pagos"]

            # Obtener el carrito del usuario
            carrito = carritos_collection.find_one({"user_id": user_id})
            
            if not carrito or not carrito.get("productos"):
                messages.error(request, "Tu carrito está vacío. No se puede procesar el pago.")
                return redirect("carrito")

            productos = carrito["productos"]

            # Registrar el pago en la colección "Pagos"
            pago = {
                "user_id": user_id,
                "monto": monto,
                "productos": productos,
                "fecha": datetime.now(),  # Fecha actual cuando se realiza el pago
                "metodo_pago": metodo_pago
            }

            # Insertar el pago en la base de datos
            pago_id = pagos_collection.insert_one(pago).inserted_id

            # Limpiar el carrito después del pago
            carritos_collection.update_one(
                {"user_id": user_id},
                {"$set": {"productos": []}}  # Vaciar el carrito
            )

            messages.success(request, "Pago procesado correctamente.")
            return redirect("confirmacion_pago", pago_id=pago_id)  # Redirigir a una página de confirmación de pago

        except Exception as e:
            # Manejar el error y redirigir al usuario con un mensaje
            messages.error(request, f"Hubo un error al procesar el pago: {str(e)}")
            return redirect("carrito") 

        finally:
            client.close()

    return render(request, "pago.html")



#Vista de confirmacion del pago
def confirmacion_pago(request, pago_id):
    try:
        # Conectar a MongoDB
        client = MongoClient('localhost', 27017)
        db = client["Amazonas"]
        pagos_collection = db["Pagos"]

        # Obtener el pago con el pago_id
        pago = pagos_collection.find_one({"_id": ObjectId(pago_id)})

        if pago:
            # Calcular la fecha de envío (1 semana después de la fecha de pago)
            fecha_pago = pago["fecha"]
            fecha_envio = fecha_pago + timedelta(days=7)
            
            # Convertir la fecha de envío a un formato legible
            fecha_envio_str = fecha_envio.strftime("%d de %B de %Y")

            return render(request, "confirmacion_pago.html", {
                "pago": pago,
                "fecha_envio": fecha_envio_str
            })
        else:
            return render(request, "error.html", {"mensaje": "Pago no encontrado."})

    except Exception as e:
        # Manejar errores de la conexión o cualquier otro error
        messages.error(request, f"Error al obtener el pago: {str(e)}")
        return redirect("index")
    
    finally:
        client.close()
        
        

#Vista para mostrar pedidos
@login_required
def mostrar_pedidos(request):
    # Obtener el user_id como string para comparar con MongoDB
    user_id = str(request.user.id)

    try:
        # Conectar a MongoDB
        client = MongoClient('localhost', 27017)
        db = client['Amazonas']
        pagos_collection = db['Pagos']

        # Imprimir el user_id para depuración
        print(f"Buscando pedidos para el user_id: {user_id}")

        # Obtener los pagos (pedidos) del usuario, ahora comparando como string
        pagos = pagos_collection.find({"user_id": user_id})

        # Verificar si se encontraron pagos
        pagos_list = list(pagos)  # Convertir el cursor en una lista para verificar
        print(f"Pedidos encontrados: {len(pagos_list)}")

        # Agregar la fecha de envío a cada pago
        for pago in pagos_list:
            # Renombrar _id a pedido_id
            pago["pedido_id"] = str(pago["_id"])  # Convertir ObjectId a string
            
            # Calcular la fecha estimada de envío
            fecha_pago = pago["fecha"]
            fecha_envio = fecha_pago + timedelta(days=7)  # Sumar 7 días para la fecha de envío
            pago["fecha_envio"] = fecha_envio.strftime("%d de %B de %Y")  # Convertir a formato legible

        return render(request, 'mostrar_pedidos.html', {'pagos': pagos_list})

    except Exception as e:
        # Manejar errores de la conexión o cualquier otro error
        messages.error(request, f"Error al cargar los pedidos: {str(e)}")
        return redirect("index")  # O redirigir a cualquier otra página deseada

    finally:
        client.close()
        

#Vista para mostrar Acerca de
def acerca_de_nosotros(request):
    return render(request, 'acerca.html')


#Vista para mostrar FAQ
def preguntas_frecuentes(request):
    return render(request, 'faq.html')