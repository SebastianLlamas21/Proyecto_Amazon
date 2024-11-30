from django.urls import path
from . import views

urlpatterns = [
	path('', views.index, name='index'), 
	path('carrito/', views.carrito, name='carrito'), 
	path('inicio/', views.inicio, name='inicio'), 
	path('pago/', views.pago, name='pago'), 
	path('sesion_iniciada/', views.sesion_iniciada, name='sesion_iniciada'), 
	path('registro/', views.registro, name='registro'),
 	path('buscar/', views.buscar_productos, name='buscar'), 
]