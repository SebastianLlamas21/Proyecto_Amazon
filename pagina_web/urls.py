from django.urls import path
from . import views

urlpatterns = [
	path('', views.index, name='index'), 
	path('carrito/', views.carrito, name='carrito'), 
	path('inicio/', views.inicio, name='inicio'), 
	path('pago/', views.pago, name='pago'), 
	path('registro/', views.registro, name='registro'), 
]