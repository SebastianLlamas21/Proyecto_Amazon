from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.generic import View, ListView, CreateView, DeleteView

#Vista Index
def index(request):
	return render(request, 'index.html') 


# Vista "Carrito"
def carrito(request):
	return render(request, "carrito.html")  


# Vista Inicio
def inicio(request):
	return render(request, "inicio.html") 


#Vista Pago
def pago(request):
	return render(request, "pago.html") 


#Registro
def registro(request):
	return render(request, "registro.html") 