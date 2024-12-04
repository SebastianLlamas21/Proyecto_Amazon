from django.urls import path
from . import views

urlpatterns = [
	path('', views.index, name='index'), 
	path('carrito/', views.carrito, name='carrito'), 
	path('inicio/', views.inicio, name='inicio'), 
	path('pago/', views.pago, name='pago'), 
	path('registro/', views.registro, name='registro'),
 	path('buscar/', views.buscar_productos, name='buscar'), 
  	path('logout/', views.logout_view, name='logout'),
  	path('agregar_al_carrito/', views.agregar_al_carrito, name='agregar_al_carrito'),
  	path('eliminar_del_carrito/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
  	path('actualizar_carrito/', views.actualizar_carrito, name='actualizar_carrito'),
   	path('procesar_pago/', views.procesar_pago, name='procesar_pago'),
    path('confirmacion_pago/<str:pago_id>/', views.confirmacion_pago, name='confirmacion_pago'),
    path('mis_pedidos/', views.mostrar_pedidos, name='mostrar_pedidos'),
    path('acerca_de_nosotros/', views.acerca_de_nosotros, name='acerca_de_nosotros'),
    path('preguntas_frecuentes/', views.preguntas_frecuentes, name='preguntas_frecuentes'),
]