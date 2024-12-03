from django.contrib.auth.models import User
from pymongo import MongoClient
from django.contrib.auth.hashers import make_password

def sync_users():
    try:
        client = MongoClient('localhost', 27017)
        db = client['Amazonas']
        collection = db['usuarios']

        # Obtener todos los usuarios de MongoDB
        usuarios = collection.find()

        for usuario in usuarios:
            email = usuario.get("Email")
            username = usuario.get("Name")
            password = usuario.get("Password")

            if not email or not username:
                print(f"Usuario con datos incompletos omitido: {usuario}")
                continue

            if not password:
                print(f"Usuario {username} no tiene contraseña. Se asignará una predeterminada.")
                password = make_password("password123")  # Contraseña predeterminada
            
            # Si el password no está cifrado en formato compatible con Django, cifrarlo
            if not password.startswith('pbkdf2'):
                password = make_password(password)

            # Verificar si el usuario ya existe en Django
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                print(f"Usuario {username} sincronizado con Django.")
            else:
                print(f"El usuario {username} ya existe en Django.")
    except Exception as e:
        print(f"Error al sincronizar usuarios: {e}")
    finally:
        client.close()
