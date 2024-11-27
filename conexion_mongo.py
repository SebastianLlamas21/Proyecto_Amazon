from pymongo import MongoClient

try:
    client = MongoClient('localhost', 27017)

    database = client['Amazonas']

    collection = database['Productos']

    documentos = collection.find()
    
    for documento in documentos:
        print(documento)
        print("\n")
except Exception as ex:
    print("Error durante la conexion: {}".format(ex))
finally:
    client.close()
    print("Conexion Finalizada")