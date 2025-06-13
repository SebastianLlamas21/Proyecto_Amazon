from django.shortcuts import render, redirect
from django.http import JsonResponse
from pymongo import MongoClient
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from bson import ObjectId
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.template.loader import render_to_string
import weasyprint
from datetime import datetime, date
from django.contrib import messages
from django.shortcuts import redirect, render
from weasyprint import HTML


# Configuración de conexión a MongoDB
def conectar_mongo():
    try:
        # Conectarse al servidor de MongoDB
        client = MongoClient('localhost', 27017)
        db = client['Amazonas']  # Aquí definimos la base de datos de conexión
        return db
    except Exception as e:
        print(f"Error al conectar con MongoDB: {str(e)}")
        return None

        
        
 # Función base para conectar y obtener una colección de MongoDB
def obtener_coleccion(request, coleccion_name):
    db = conectar_mongo()
    if db is None:
        return JsonResponse({"error": "Error al conectar con la base de datos."}, status=500)
    
    collection = db[coleccion_name]  # Obtiene la colección específica
    
    # Retornamos la colección para que la vista la use
    return collection

   
#Vista Index
def index(request):
    productos = []  # Lista para almacenar los productos

    try:
        collection = obtener_coleccion(request, 'Productos')  # Especificamos la colección 'Productos'
        categorias = collection.distinct("category")

        if isinstance(collection, JsonResponse):  # Si la conexión falló, devolvemos el error
            return collection

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
    
    
    # Pasar los productos al template
    return render(request, 'index.html', {"productos": productos, "categorias": categorias})


#Inicio de sesion
def inicio(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        try:
            # Conexión a MongoDB
            collection = obtener_coleccion(request, 'usuarios')  # Especificamos la colección 'Productos'
            if isinstance(collection, JsonResponse):  # Si la conexión falló, devolvemos el error
                return collection

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


    return render(request, "inicio.html")

#Vista de logout
def logout_view(request):
    """Cerrar la sesión del usuario."""
    if request.user.is_authenticated:
        try:
            # Conexión a MongoDB
            collection = obtener_coleccion(request, 'usuarios')  # Especificamos la colección 'Productos'
            if isinstance(collection, JsonResponse):  # Si la conexión falló, devolvemos el error
                return collection

            # Actualizar el estado de sesión en MongoDB
            collection.update_one(
                {"Email": request.user.email},  # Suponiendo que el email identifica al usuario
                {"$set": {"Sesion": False}}
            )
        except Exception as e:
            print(f"Error al actualizar el estado de sesión en MongoDB: {e}")
        
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
            collection = obtener_coleccion(request, 'Productos')  # Especificamos la colección 'Productos'
            if isinstance(collection, JsonResponse):  # Si la conexión falló, devolvemos el error
                return collection

            # Buscar productos cuyo nombre coincida parcialmente (insensible a mayúsculas)
            resultados = collection.find({"name": {"$regex": termino, "$options": "i"}})

            # Convertir los resultados a una lista de diccionarios
            productos = [
                {"id": str(producto["_id"]),"name": producto["name"], "price": producto["price"], "images": producto["images"]}
                for producto in resultados
            ]

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

    try:
        # Conectar a MongoDB usando la función centralizada
        db = conectar_mongo()
        if db is None:
            messages.error(request, "Error al conectar con la base de datos.")
            return redirect("inicio")

        carritos_collection = db["Carritos"]

        # Obtener el carrito del usuario desde MongoDB
        carrito = carritos_collection.find_one({"user_id": str(request.user.id)})

        if carrito:
            # Procesar los productos del carrito
            for item in carrito.get("productos", []):
                productos.append({
                    "producto_id": str(item["producto_id"]),  # Convertir ObjectId a string si es necesario
                    "name": item["name"],
                    "price": item["price"],
                    "cantidad": item["cantidad"],
                    "images": item.get("images", [])
                })
                # Calcular el subtotal
                subtotal += item.get("price", 0) * item.get("cantidad", 1)
        else:
            messages.info(request, "Tu carrito está vacío.")

    except Exception as e:
        messages.error(request, f"Error al cargar el carrito: {e}")
    
    # Definir el costo de envío basado en el subtotal
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
                # Usar la conexión centralizada a MongoDB
                db = conectar_mongo()
                if db is None:
                    messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
                    return redirect("index")

                productos_collection = db["Productos"]
                carritos_collection = db["Carritos"]

                # Usar el ID del usuario como cadena
                usuario_id = str(request.user.id)

                # Buscar el producto en la colección 'Productos'
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
            
        else:
            messages.error(request, "No se ha proporcionado un ID de producto válido o no estás autenticado.")
        
    return redirect("index")


#Vista para eliminar productos del carrito
def eliminar_del_carrito(request):
    if request.method == "POST" and request.user.is_authenticated:
        producto_id = request.POST.get("producto_id")

        try:
            # Usar la conexión centralizada a MongoDB
            db = conectar_mongo()
            if db is None:
                messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
                return redirect("carrito")

            carritos_collection = db["Carritos"]

            # Eliminar el producto del carrito
            carritos_collection.update_one(
                {"user_id": str(request.user.id)},
                {"$pull": {"productos": {"producto_id": ObjectId(producto_id)}}}
            )

            messages.success(request, "Producto eliminado del carrito.")
        except Exception as e:
            messages.error(request, f"Error al eliminar el producto: {e}")

    return redirect("carrito")


#Vista para actulizar cantidad de producto en carrito
def actualizar_carrito(request):
    if request.method == "POST" and request.user.is_authenticated:
        producto_id = request.POST.get("producto_id")
        cantidad = int(request.POST.get("cantidad", 1))

        try:
            # Usar la conexión centralizada a MongoDB
            db = conectar_mongo()
            if db is None:
                messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
                return redirect("carrito")

            carritos_collection = db["Carritos"]

            # Actualizar la cantidad en el carrito
            carritos_collection.update_one(
                {"user_id": str(request.user.id), "productos.producto_id": ObjectId(producto_id)},
                {"$set": {"productos.$.cantidad": cantidad}}
            )

            #messages.success(request, "Cantidad actualizada.")
        except Exception as e:
            messages.error(request, f"Error al actualizar el carrito: {e}")

    return redirect("carrito")



#Vista Pago
def pago(request):
    total = request.GET.get('total', 0)  # Recibir el valor total desde el carrito (GET)
    
    try:
        total = float(total)  # Convertir a float si es necesario
    except ValueError:
        total = 0.0

    return render(request, "pago.html", {"total_pago": total})


#Validacion del Pago Aloritmo de Luhn
def validar_luhn(numero):
    numero = numero.replace(' ', '')
    if not numero.isdigit():
        return False
    suma = 0
    debe_duplicar = False
    for digito in reversed(numero):
        d = int(digito)
        if debe_duplicar:
            d *= 2
            if d > 9:
                d -= 9
        suma += d
        debe_duplicar = not debe_duplicar
    return suma % 10 == 0


#Vista para procesar el pago
def procesar_pago(request):
    if request.method == 'POST':
        user_id = str(request.user.id) if request.user.is_authenticated else None
        nombre_tarjeta = request.POST.get('card_name', '').strip()
        numero_tarjeta = request.POST.get('card_number', '').strip()
        expiry_date = request.POST.get('expiry_date', '').strip()
        cvv = request.POST.get('cvv', '').strip()
        monto = request.POST.get('monto', '0').strip()

        # Para mostrar en caso de error y que el usuario no pierda datos
        context = {
            'total_pago': monto,
            'card_name': nombre_tarjeta,
            'card_number': numero_tarjeta,
            'expiry_date': expiry_date,
            'cvv': cvv,
        }

        # Validar monto
        try:
            monto = float(monto)
            if monto <= 0:
                messages.error(request, "Monto inválido.")
                return render(request, 'pago.html', context)
        except:
            messages.error(request, "Monto inválido.")
            return render(request, 'pago.html', context)

        # Validar número tarjeta con Luhn
        if not validar_luhn(numero_tarjeta):
            messages.error(request, "Número de tarjeta inválido.")
            return render(request, 'pago.html', context)

        # Validar fecha de expiración
        try:
            anio, mes = map(int, expiry_date.split('-'))
            fecha_venc = date(anio, mes, 1)
            hoy = date.today().replace(day=1)
            if fecha_venc < hoy:
                messages.error(request, "La fecha de vencimiento debe ser futura.")
                return render(request, 'pago.html', {
                    'total_pago': monto,
                    'card_name': nombre_tarjeta,
                    'card_number': numero_tarjeta,
                    'expiry_date': expiry_date,
                    'cvv': cvv
                })
        except Exception:
            messages.error(request, "Fecha de vencimiento inválida.")
            return render(request, 'pago.html', {
                'total_pago': monto,
                'card_name': nombre_tarjeta,
                'card_number': numero_tarjeta,
                'expiry_date': expiry_date,
                'cvv': cvv
            })
            
            
        # Validar CVV (3 o 4 dígitos numéricos)
        if not (cvv.isdigit() and len(cvv) in [3, 4]):
            messages.error(request, "CVV inválido.")
            context = {
                "total_pago": monto,
                "card_name": nombre_tarjeta,
                "card_number": numero_tarjeta,
                "expiry_date": expiry_date,
                "cvv": cvv
            }
            return render(request, "pago.html", context)

        metodo_pago = "Tarjeta"

        # Procesar pago en MongoDB
        try:
            db = conectar_mongo()
            if db is None:
                messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
                return redirect("carrito")

            carritos_collection = db["Carritos"]
            pagos_collection = db["Pagos"]

            carrito = carritos_collection.find_one({"user_id": user_id})
            if not carrito or not carrito.get("productos"):
                messages.error(request, "Tu carrito está vacío. No se puede procesar el pago.")
                return redirect("carrito")

            productos = carrito["productos"]

            pago = {
                "user_id": user_id,
                "monto": monto,
                "productos": productos,
                "fecha": datetime.now(),
                "metodo_pago": metodo_pago,
                "nombre_tarjeta": nombre_tarjeta,
                "numero_tarjeta": numero_tarjeta,
                "expiry_date": expiry_date,
            }

            pago_id = pagos_collection.insert_one(pago).inserted_id

            carritos_collection.update_one(
                {"user_id": user_id},
                {"$set": {"productos": []}}
            )

            messages.success(request, "Pago procesado correctamente.")
            return redirect("confirmacion_pago", pago_id=pago_id)

        except Exception as e:
            messages.error(request, f"Hubo un error al procesar el pago: {str(e)}")
            return redirect("carrito")

    else:
        # GET request: mostrar formulario vacío o con total si viene por GET
        total = request.GET.get('total', '0')
        context = {'total_pago': total}
        return render(request, "pago.html", context)




#Vista de confirmacion del pago
def confirmacion_pago(request, pago_id):
    try:
        # Usar la conexión centralizada a MongoDB
        db = conectar_mongo()
        if db is None:
            messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
            return redirect("index")

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
                "pago_id": pago_id,  # <- Agregamos pago_id aquí
                "fecha_envio": fecha_envio_str
            })
        else:
            return render(request, "error.html", {"mensaje": "Pago no encontrado."})

    except Exception as e:
        messages.error(request, f"Error al obtener el pago: {str(e)}")
        return redirect("index")

        
        

#Vista para mostrar pedidos
@login_required
def mostrar_pedidos(request):
    # Obtener el user_id como string para comparar con MongoDB
    user_id = str(request.user.id)

    try:
        # Usar la conexión centralizada a MongoDB
        db = conectar_mongo()
        if db is None:
            messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
            return redirect("index")

        pagos_collection = db['Pagos']

        # Obtener los pagos (pedidos) del usuario, ahora comparando como string
        pagos = pagos_collection.find({"user_id": user_id})

        # Verificar si se encontraron pagos
        pagos_list = list(pagos)  # Convertir el cursor en una lista para verificar

        if not pagos_list:
            messages.info(request, "No tienes pedidos recientes.")
            return render(request, 'mostrar_pedidos.html', {'pagos': []})

        # Agregar la fecha de envío a cada pago
        pagos_limpios = []

        for pago in pagos_list:
            pago_limpio = {
                "pedido_id": str(pago["_id"]),
                "fecha": pago["fecha"],
                "monto": pago["monto"],
                "productos": pago["productos"],
                "fecha_envio": (pago["fecha"] + timedelta(days=7)).strftime("%d de %B de %Y"),
                "estado": pago.get("estado", "Sin especificar"),
            }
            pagos_limpios.append(pago_limpio)

        return render(request, 'mostrar_pedidos.html', {'pagos': pagos_limpios})

    except Exception as e:
        # Manejar errores de la conexión o cualquier otro error
        messages.error(request, f"Error al cargar los pedidos: {str(e)}")
        return redirect("index")  # O redirigir a cualquier otra página deseada
        

#Vista para mostrar Acerca de
def acerca_de_nosotros(request):
    return render(request, 'acerca.html')


#Vista para mostrar FAQ
def preguntas_frecuentes(request):
    return render(request, 'faq.html')

#Categorizacion
def categoria(request, nombre_categoria):
    collection = obtener_coleccion(request, 'Productos')
    productos = []
    documentos = collection.find({"category": nombre_categoria})
    for doc in documentos:
        productos.append({
            "id": str(doc.get("_id")),
            "name": doc.get("name"),
            "price": doc.get("price"),
            "images": doc.get("images", [])
        })
    return render(request, 'categoria.html', {
        "productos": productos,
        "categoria": nombre_categoria
    })

def generar_factura(request, pago_id):
    try:
        db = conectar_mongo()
        if db is None:
            messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
            return redirect("index")

        pagos_collection = db["Pagos"]
        facturas_collection = db["Facturas"]

        pago = pagos_collection.find_one({"_id": ObjectId(pago_id)})

        if not pago:
            messages.error(request, "Pago no encontrado.")
            return redirect("index")

        # Preparar datos de la factura
        fecha_pago = pago["fecha"]
        fecha_envio = fecha_pago + timedelta(days=7)

        factura_data = {
            "pago_id": pago["_id"],
            "usuario_id": pago.get("usuario_id"),  # si tienes referencia a usuario
            "productos": pago.get("productos", []),
            "total": pago.get("total"),
            "fecha_pago": fecha_pago,
            "fecha_envio": fecha_envio,
            "fecha_generacion": datetime.now(),
        }

        # Guardar la factura
        factura_id = facturas_collection.insert_one(factura_data).inserted_id

        # Redirigir a la vista de mostrar factura o descargar PDF
        return redirect('mostrar_factura', factura_id=str(factura_id))

    except Exception as e:
        messages.error(request, f"Error al generar factura: {str(e)}")
        return redirect("index")
    
    
def mostrar_factura(request, factura_id):
    try:
        db = conectar_mongo()
        if db is None:
            messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
            return redirect("index")

        facturas_collection = db["Facturas"]
        factura = facturas_collection.find_one({"_id": ObjectId(factura_id)})

        if not factura:
            messages.error(request, "Factura no encontrada.")
            return redirect("index")

        return render(request, "factura.html", {
            "factura": factura
        })

    except Exception as e:
        messages.error(request, f"Error al mostrar factura: {str(e)}")
        return redirect("index")
    
    
def factura_pdf(request, factura_id):
    try:
        db = conectar_mongo()
        if db is None:
            messages.error(request, "No se pudo conectar a la base de datos MongoDB.")
            return redirect("index")

        facturas_collection = db["Facturas"]
        factura = facturas_collection.find_one({"_id": ObjectId(factura_id)})

        if not factura:
            messages.error(request, "Factura no encontrada.")
            return redirect("index")

        html_string = render_to_string("factura.html", {"factura": factura})

        pdf_file = weasyprint.HTML(string=html_string).write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="factura_{factura_id}.pdf"'

        return response

    except Exception as e:
        messages.error(request, f"Error al generar PDF: {str(e)}")
        return redirect("index")
    
    
def pago_realizado(request, pago_id):
    db = conectar_mongo()
    pagos = db["Pagos"]
    pago = pagos.find_one({"_id": ObjectId(pago_id)})
    if not pago:
        messages.error(request, "Pago no encontrado.")
        return redirect("carrito")
    
    numero_tarjeta = pago.get('numero_tarjeta', '')
    ultimos4 = numero_tarjeta[-4:] if len(numero_tarjeta) >= 4 else '****'
    nombre_tarjeta = pago.get('nombre_tarjeta', 'Titular')

    # Calcular subtotales y total
    for prod in pago.get("productos", []):
        try:
            cantidad = float(prod.get("cantidad", 0))
            precio = float(prod.get("price", 0))  # aquí price
            prod["subtotal"] = cantidad * precio
        except (ValueError, TypeError):
            prod["subtotal"] = 0.0

    pago["total"] = sum(p.get("subtotal", 0) for p in pago.get("productos", []))

    # Pasa el _id como id para evitar problema con guion bajo
    pago["id"] = str(pago["_id"])

    # Fecha estimada envío
    fecha_envio = pago["fecha"] + timedelta(days=7)

    context = {
        "factura": pago,
        "fecha_envio": fecha_envio.strftime("%d de %B de %Y"),
        'numero_tarjeta': numero_tarjeta,
        'tarjeta_ultimos4': ultimos4,
        'nombre_tarjeta': nombre_tarjeta,
    }

    html = render_to_string('factura.html', context)
    pdf = HTML(string=html).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=factura_{pago_id}.pdf'
    return response