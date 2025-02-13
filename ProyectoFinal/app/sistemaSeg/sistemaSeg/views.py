from django.http import HttpResponse, JsonResponse
from django.template import Template, Context
from django.shortcuts import render, redirect
from django.conf import settings
from modelo import models
from django.utils.crypto import get_random_string
from datetime import timezone
from sistemaSeg.decoradores import login_requerido_alumnos, login_requerido_profesor, login_requerido , login_requerido2
import logging, platform
import sistemaSeg.settings as conf
import datetime
import subprocess
import requests
import string
import random
import re
import hashlib
import os, sys, stat
import mensajes
import socket
import shutil
import glob
import threading
import logging, platform
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist




def conectar_servidor(host, puerto):
    """
    Funcion que se utiliza para poder realizar la conexion al servidor

    Keyword Arguments:
    host: str
    puerto: int
    returns: cliente 
    """
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        cliente.connect((host, int(puerto)))
        logging.info("Se establecio la conexion al servidor de pruebas")
        return cliente
    except:
        print('Servidor inalcanzable')
        logging.error('No se establecio la conexion con el servidor de ejecucion de scripts')
        exit()

def leer_mensajes(cliente):
    """
    Funcion que permite leer los mensajes y mandarlos decodificados

    Keyword Arguments:
    ip: str
    returns: mensaje.decode
    """
     mensaje = mensajes.leer_mensaje(cliente)
     return mensaje.decode('utf-8')


def enviar_mensaje_loop(cliente,ruta,esperada,salida):
    """
    Funcion que realiza el envio de mensajes al servidor de pruebas de scripts

    Keyword Arguments:
    cliente: str
    ruta: str
    esperada: str
    salida: str
    returns: None
    """
    mensaje = ruta + '|' + esperada + '|' + salida
    mensaje = mensaje.encode('utf-8')
    mensajes.mandar_mensaje(cliente, mensaje)

def copiar_ruta_tmp(ruta):
    """
    Funcion que permite copiar  las ruta que se nos proporciona

    Keyword Arguments:
    ruta: str
    returns: bool
    """
    lista = r"/evaluacion/EvalScript-*"
    directorio = glob.glob(lista)
    ruta_directorio = ''.join(directorio)
    ruta_copia = shutil.copy(ruta, ruta_directorio)
    os.chmod(ruta_copia, 0o755)
    return ruta_copia

def comparar_script(entradaScript, esperadaScript, archivo):
    """
    Funcion que se funcion para llevar acabo la comparcion de scripts

    Keyword Arguments:
    ip: str
    returns: bool
    """
    os.chmod(archivo, 0o755)
    comando = [archivo, entradaScript]
    salida = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = salida.communicate()

    if esperadaScript == stdout.decode('utf-8').strip():
        return True
    else:
        return False

def comparar_resultados(res_maestro, res_alumno,request):
    """
    Funcion que permite la comparacion de los resultados de la ejecucion de los script
    del alumno y del maestro 
    Keyword Arguments:
    res_maestro: str
    res_alumno: str
    request: --
    returns: bool
    """
    if res_alumno == res_maestro:
        correcto = 'Correcto'
        messages.success(request, "Los resultados son iguales")
        return correcto
    else:
        incorrecto = 'Incorrecto'
        messages.success(request, "Los resultados NO son iguales")
        return incorrecto



@login_requerido_profesor
def crear_actividad(request):
    """
    Vista que permite la definicion de actividades 
    Keyword Arguments:
    request --
    returns: HTTP_Response
    """
    t = 'crear_ejercicio.html'
    if request.method == 'GET':
        return render(request,t)
    elif request.method == 'POST':
        titulo = request.POST.get('Titulo','')
        descripcion = request.POST.get('Descripcion','')
        entrada = request.POST.get('entrada', '')
        esperada = request.POST.get('esperada','')
        archivo = request.FILES.get('archivosubido')
        nombre = request.session.get('nombre')
        id_profe = models.Profesor.objects.get(NombreProfesor=nombre)
        practica = models.Practicas(NombrePractica=titulo,Descripcion=descripcion,Entrada=entrada, Esperada=esperada, Archivo=archivo, practica_profesor_id=id_profe.id)
        practica.save()
        logging.info("Se creo la actividad correctamente" + titulo)
        return render(request, t)

@login_requerido_alumnos
def listar_ejercicios(request):

    """
    Vista que permite la visibiliacion de la lista de ejercicios definidos por el maestro 
    Keyword Arguments:
    request --
    returns: HTTP_Response

    """
    t = 'listar_ejercicios.html'
    bots =  models.Practicas.objects.all()
    return render(request,t,{'bots':bots})

@login_requerido_profesor
def listar_alumnos(request):
    """
    Vista que permite la visibiliacion de la lista de los alumnos que subieron las actidades 
    Keyword Arguments:
    request --
    returns: HTTP_Response
    """
    t = 'listar_alumnos.html'
    alumnos = models.ArchivosA.objects.all()
    return render(request,t,{'alumnos':alumnos})


@login_requerido_alumnos
   
def verificar_scripts(request, id):
  """
  Vista que permite verificacion de script que se subio  
  Keyword Arguments:
  request --
  returns: HTTP_Response
  """
  t = 'subir_ejercicios.html'
  host = '0.0.0.0'
  puerto = 8002
  if request.method == 'GET':
       bot = models.Practicas.objects.get(id=id)
       return render(request,t,{'bot':bot})
  elif request.method == 'POST':
    bot = models.Practicas.objects.get(id=id)
    
    nombre_usuario = request.session.get('nombre')
    practica = models.Practicas.objects.get(pk=id)
    entrada = practica.Entrada
    esperada = practica.Esperada

    file = request.FILES.get('archivosubido')
    obtener_alumno = models.Alumnos.objects.get(NombreAlumno=nombre_usuario)
    archivo = models.ArchivosA(upload=file, usuario=obtener_alumno)
    archivo.save()
    

    obj = models.ArchivosA.objects.get(upload=archivo.upload, usuario_id=obtener_alumno)

    ruta = obj.upload.path
    rutaM = practica.Archivo.path

    ruta_archivo_tmp = copiar_ruta_tmp(ruta)
    ruta_archivo_tmp_maestro = copiar_ruta_tmp(rutaM)


    cliente = conectar_servidor(host, puerto)
    enviar_mensaje_loop(cliente,ruta_archivo_tmp,entrada,esperada)
    msj = leer_mensajes(cliente)

    cliente2 = conectar_servidor(host, puerto)
    enviar_mensaje_loop(cliente2,ruta_archivo_tmp_maestro,entrada,esperada)
    msj2 = leer_mensajes(cliente2)   

    resultado = comparar_resultados(msj,msj2,request)

    models.ArchivosA.objects.filter(usuario_id=obtener_alumno, upload=archivo.upload).update(estado=resultado)

    return render(request,t,{'bot':bot})


def mandar_mensaje_al_bot(request):
    """
    Funcion que permite mandar el token al bot alumno para poder permitir la autenticacion

    Keyword Arguments:
    request --
    returns:--
    """
    nombre = request.session.get('nombre','anonimo')
    datos_guardados = models.Alumnos.objects.get(NombreAlumno=nombre)
    Chat_id = datos_guardados.Chat_id
    token = datos_guardados.Token_tel
    mensaje_bot = ''.join(random.sample(string.ascii_letters + string.digits, 8))
    send_text = 'https://api.telegram.org/bot' + token + '/sendMessage?chat_id=' + Chat_id + '&parse_mode=Markdown&text='+ mensaje_bot
    requests.get(send_text)
    models.Alumnos()
    logging.info("Se le envio el token para la autenticacion a el usuario:" + nombre)
    models.Alumnos.objects.filter(NombreAlumno=nombre).update(Token_Env=mensaje_bot, Token_Tem=datetime.datetime.now(), Estado_token="Valido")

def mandar_mensaje_al_bot_profesor(request):
    """
    Funcion que permite mandar el token al bot profesor para poder permitir la autenticacion

    Keyword Arguments:
    request --
    returns:--
    """
    nombre = request.session.get('nombre','anonimo')
    datos_guardados = models.Profesor.objects.get(NombreProfesor=nombre)
    Chat_id = datos_guardados.Chat_id
    token = datos_guardados.Token_tel
    mensaje_bot = ''.join(random.sample(string.ascii_letters + string.digits, 8))
    send_text = 'https://api.telegram.org/bot' + token + '/sendMessage?chat_id=' + Chat_id + '&parse_mode=Markdown&text='+ mensaje_bot
    requests.get(send_text)
    models.Profesor()
    logging.info("Se le envio el token para la autenticacion a el usuario:" + nombre)
    models.Profesor.objects.filter(NombreProfesor=nombre).update(Token_Env=mensaje_bot, Token_Tem=datetime.datetime.now(), Estado_token="Valido")
    

def disminuir_tiempo_actual_yalmaceno(tiempo_almacenado):
    """
    Funcion que permite diminucion del timepo de vida de toke que se le fue enviado al bot

    Keyword Arguments:
    tiempo_almacenado: datatime
    return: time
    """
    tiempo_actual = datetime.datetime.now(timezone.utc)
    diferencia = tiempo_actual - tiempo_almacenado
    logging.info("Se disminuye el tiempo de vida del token")
    return diferencia.seconds    

@login_requerido
def verificar_token(request):
    """
    Vista que permite la verificacion del token mandado al alumno y pemirte la autenticacion del mismo

    Keyword Arguments:
    request --
    returns: HTTP_Response
    """
    t = 'verficiacion_token.html'
    nombre = request.session.get('nombre','anonimo')
    if request.method == 'GET':
        return render(request, t)
    elif request.method == 'POST':
        ip_cliente = get_client_ip(request)
        if puede_hacer_peticion(ip_cliente):
           token = request.POST.get('Token','').strip()
           try:
               token_almacenado = models.Alumnos.objects.get(Token_Env=token)
               if (disminuir_tiempo_actual_yalmaceno(token_almacenado.Token_Tem) > 160):  
                    errores={'El token ha expirado'}
                    logging.error('El token ha expierado', token_almacenado)
                    return render(request,t,{'errores':errores})
               request.session['logueado2'] = True
               request.session['nombre'] = nombre
               logging.info("usuario logueado:" + nombre)
               models.Alumnos.objects.filter(NombreAlumno=nombre).update(Estado_token="Invalido")
               alumno = models.Alumnos.objects.get(NombreAlumno=nombre)
               if token_almacenado.Estado_token == "Invalido":
                  errores =['Token ya utilizado']
                  logging.error('El token ya fue utilizado', token_almacenado)
                  return render(request,t,{'errores': errores})
               elif alumno.Tipocuenta == 'Alumno':
                  return redirect('/listar_ejercicios')
               
                     
           except:
               errores = ['token incorrecto']
               logging.error('El token que se utilizo fue incorrecto', token_almacenado)
               return render(request, "login.html", {'errores': errores})
        else:
           return HttpResponse("Agotaste tus intentos espera 1 minuto")

@login_requerido            
def verificar_token_maestro(request):
    """
    Vista que permite la verificacion del token mandado al maestro y pemirte la autenticacion del mismo

    Keyword Arguments:
    request --
    returns: HTTP_Response
    """
    t = 'verficiacion_token_maestro.html'
    nombre = request.session.get('nombre','anonimo')
    if request.method == 'GET':
        return render(request, t)
    elif request.method == 'POST':
        ip_cliente = get_client_ip(request)
        if puede_hacer_peticion(ip_cliente):
           token = request.POST.get('Token','').strip()
           try:
               print('estoy en el try arriba de token almacenado')
               token_almacenado = models.Profesor.objects.get(Token_Env=token)
               print(token_almacenado.Estado_token)
               if (disminuir_tiempo_actual_yalmaceno(token_almacenado.Token_Tem) > 160):
                    print('estoy en el if abajo estan errores')
                    errores={'El token ha expirado'}
                    logging.error('El token ha expierado', token_almacenado)
                    return render(request,t,{'errores':errores})
               request.session['logueado2'] = True
               request.session['nombre'] = nombre
               logging.info("usuario logueado:" + nombre)
               print('abajo esta model profesor')
               models.Profesor.objects.filter(NombreProfesor=nombre).update(Estado_token="Invalido")
               profesor = models.Profesor.objects.get(NombreProfesor=nombre)
               print(token_almacenado.Estado_token)
               if token_almacenado.Estado_token == "Invalido":
                  errores =['Token ya utilizado']
                  logging.error('El token ya fue utilizado', token_almacenado)
                  return render(request,t,{'errores': errores})
               elif profesor.Tipocuenta == 'Maestro':
                  return redirect('/crear_actividad')
               
        
           except:
               errores = ['token incorrecto']
               logging.error('El token que se utilizo fue incorrecto', token_almacenado)
               return render(request, "login.html", {'errores': errores})
        else:
           return HttpResponse("Agotaste tus intentos espera 1 minuto")



def login(request):
  logueado = request.session.get('logueado', False)
  if request.method == 'GET':
        return render(request, 'login.html', {'logueado':logueado})
  elif request.method == 'POST':
        errores = []
        nombre = request.POST.get('nombres', '').strip()
        tipousuario = request.POST.get('Tipousuario', '').strip()
        contraseña = request.POST.get('password', '').strip()
        nombre_usuario = request.session.get('nombre')
                
        if tipousuario == 'Alumno':
           if nombre and contraseña and tipousuario:
              if puede_hacer_peticion(get_client_ip(request)):
                 try:
                     try:
                         alumno = models.Alumnos.objects.get(NombreAlumno=nombre)
                     except ObjectDoesNotExist: 
                            errores = ['Alumno no existe']
                            return render(request, 'login.html', {'errores':errores})    
                     if password_valido(contraseña, alumno.Contraseña, alumno.salt):
                         request.session['logueado']= True
                         request.session['nombre']= nombre
                         mandar_mensaje_al_bot(request)
                         return redirect('/verificar_token') 
                         logging.info("Se redireccino a la verificacion del tokenal usuario:" + nombre)
                     else:
                         
                         errores.append('Usuario o contraseña inválidos alumno')
                         logging.error('Usuario o contraseña inválidos alumno')
                 except:
                        errores.append('Usuario o contraseña inválidos alumno')
                        logging.error('Usuario o contraseña inválidos alumno')
              else:
                    return HttpResponse("Agotaste tus intentos espera 1 minuto")
                    logging.error('Agotaste tus intentos espera 1 minuto')
           else:
                 errores.append('No se pasaron las variables correctas en el formulario')
                 logging.error('No se pasaron las variables correctas en el formulario')
           return render(request, 'login.html', {'errores': errores})
        elif tipousuario == 'Maestro':
            if nombre and contraseña and tipousuario:
                if puede_hacer_peticion(get_client_ip(request)):
                   try:
                       try:
                           profesor2 = models.Profesor.objects.get(NombreProfesor=nombre)
                       except ObjectDoesNotExist: 
                              errores = ['Profesor no existe']
                              return render(request, 'login.html', {'errores':errores})   
                       if password_valido(contraseña, profesor2.Contraseña, profesor2.salt):
                           request.session['logueado']= True
                           request.session['nombre']= nombre
                           mandar_mensaje_al_bot_profesor(request)
                           return redirect('/verificar_token_maestro')
                           logging.info("Se redireccino a la verificacion del tokenal usuario:" + nombre)
                       else:
                            errores.append('Usuario o contraseña inválidos profesor')
                            logging.error('Usuario o contraseña inválidos profe')
                   except:
                          errores.append('Usuario o contraseña inválidos profesor')
                          logging.error('Usuario o contraseña inválidos profe')
                else:
                      return HttpResponse("Agotaste tus intentos espera 1 minuto")
                      logging.error('Agotaste tus intentos espera 1 minuto')
            else:
                   errores.append('No se pasaron las variables correctas en el formulario')
                   logging.error('No se pasaron las variables correctas en el formulario')
            return render(request, 'login.html', {'errores': errores})


        
@login_requerido2
def logout(request):
    """
    Vista que permite el cirre de sesion del usuario que se encuentre en el sistema.

    Keyword Arguments:
    request --
    returns: HTTP_Response
    """
    request.session['logueado'] = False
    request.session.flush()
    logging.info("El usuario cerro session")
    return redirect('/login')
 
def password_valido(password, pass_hasheado, salt):
    """
    Determina si la ip ya está en la BD.

    Keyword Arguments:
    ip: str
    returns: bool
    """
    binario = (password + salt).encode('utf-8')
    hasher = hashlib.sha256()
    hasher.update(binario)
    return hasher.hexdigest() == pass_hasheado

def verificacion_de_contrasenas(alumno):
    """
    Funcion que permite saber los errores que se tiene la contraseña del alumno al momento de ser introducida 

    Keyword Arguments:
    alumno: object
    returns: errores_contrasena
    """
    caracteres_especiales = "[@_!#$%^&*()<>?/|}{~:]";
    errores_contrasena = []
    if ' ' in alumno.Contraseña:
            errores_contrasena.append('La contraseña no debe contener espacios')
    if len(alumno.Contraseña) < 10:
               errores_contrasena.append('La contraseña debe contener al menos 10 caracteres')
    if not any(caracter.isupper() for caracter in alumno.Contraseña):
               errores_contrasena.append('La contraseña al menos debe contener una letra mayúscula')
    if not any(caracter.islower() for caracter in alumno.Contraseña):
               errores_contrasena.append('La contraseña debe de contar con al menos una letra minuscula')
    if not any(caracter.isdigit() for caracter in alumno.Contraseña):
               errores_contrasena.append('La contraseña debe de contar con al menos con un numero')
    return errores_contrasena            

def Registro_Alumnos(request):
    """
    Vista que permite el registro de usuario en el sistema

    Keyword Arguments:
    request --
    returns: HTTP_Response
    """
    t = 'registro_alumnos.html';
    if request.method == 'GET':
       return render(request,t,{})
    elif request.method == 'POST':
       nombre = request.POST.get('nombreAlumno','').strip()
       matricula = request.POST.get('Matricula','').strip()
       contrasena =  request.POST.get('Contrasena','').strip()
       Tipocuenta = request.POST.get('TipoCuenta','').strip()
       chat_id = request.POST.get('Chat_id','').strip()
       token_telegram = request.POST.get('token_tel','').strip()
       if Tipocuenta == "Alumno":
          alumno =  models.Alumnos(NombreAlumno=nombre, Matricula=matricula, Contraseña=contrasena, Tipocuenta=Tipocuenta, Chat_id=chat_id, Token_tel=token_telegram)
          errores = recoleccion_de_errores_del_registro(alumno)
       elif Tipocuenta == "Maestro":
          profesor =  models.Profesor(NombreProfesor=nombre, Matricula=matricula, Contraseña=contrasena, Tipocuenta=Tipocuenta, Chat_id=chat_id, Token_tel=token_telegram)
          errores = recoleccion_de_errores_del_registro_profesor(profesor)
       if not errores:
          Elsalt = get_random_string(length=16)
          binario = (contrasena + Elsalt).encode('utf-8')
          hasher = hashlib.sha256()
          hasher.update(binario)
          alumno = models.Alumnos(NombreAlumno=nombre, Matricula=matricula, Contraseña=hasher.hexdigest(), Tipocuenta=Tipocuenta, Chat_id=chat_id, Token_tel=token_telegram, salt=Elsalt)
          profesor = models.Profesor(NombreProfesor=nombre, Matricula=matricula, Contraseña=hasher.hexdigest(), Tipocuenta=Tipocuenta, Chat_id=chat_id, Token_tel=token_telegram, salt=Elsalt)
          if Tipocuenta == "Alumno":
             alumno.save()
             logging.info("Se guardo el registro de el alumno:" + nombre)
             return redirect('/login')
          else:
             logging.info("Se guardo el registro de el alumno:" + nombre)
             profesor.save()
             return redirect('/login')
       else:
          contexto = {'errores':errores}
          return render(request,t,contexto)



def verificacion_de_contrasenas_profesor(profesor):
    """
    Funcion que permite saber los errores que se tiene la contraseña del profesor al momento de ser introducida 

    Keyword Arguments:
    alumno: object
    returns: errores_contrasena
    """
    caracteres_especiales = "[@_!#$%^&*()<>?/|}{~:]";
    errores_contrasena = []
    if ' ' in profesor.Contraseña:
            errores_contrasena.append('La contraseña no debe contener espacios')
    if len(profesor.Contraseña) < 10:
               errores_contrasena.append('La contraseña debe contener al menos 10 caracteres')
    if not any(caracter.isupper() for caracter in profesor.Contraseña):
               errores_contrasena.append('La contraseña al menos debe contener una letra mayúscula')
    if not any(caracter.islower() for caracter in profesor.Contraseña):
               errores_contrasena.append('La contraseña debe de contar con al menos una letra minuscula')
    if not any(caracter.isdigit() for caracter in profesor.Contraseña):
               errores_contrasena.append('La contraseña debe de contar con al menos con un numero')
    return errores_contrasena

def recoleccion_de_errores_del_registro_profesor(profesor):
    """
    Determina si la ip ya está en la BD.

    Keyword Arguments:
    ip: str
    returns: bool
    """
    errores = []
    if profesor.NombreProfesor == '':
              errores.append('El nombre del usuario esta vacio')
    if profesor.Matricula == '':
              errores.append('La matricula esta vacia')
    if profesor.Contraseña == '':
              errores.append('La contraseña esta vacia')
    if profesor.Tipocuenta == '':
              errores.append('EL tipo de cuenta esta vacio')
    if profesor.Chat_id == '':
              errores.append('El chat_id del registro esta vacio')
    if profesor.Token_tel == '':
              errores.append('El token del registro esta vacio')
              
    errores_contrasena = verificacion_de_contrasenas_profesor(profesor)
    errores += errores_contrasena
    return errores


def recoleccion_de_errores_del_registro(alumno):
    """
    Funcion qu permite saber cuales son los errores al momento de llevar acabo el llenado de la informacion del formulario

    Keyword Arguments:
    alumno: object
    returns: errores[]
    """
    errores = []
    if alumno.NombreAlumno == '':
              errores.append('El nombre del usuario esta vacio')
    if alumno.Matricula == '':
              errores.append('La matricula esta vacia')
    if alumno.Contraseña == '':
              errores.append('La contraseña esta vacia')
    if alumno.Tipocuenta == '':
              errores.append('EL tipo de cuenta esta vacio')
    if alumno.Chat_id == '':
              errores.append('El chat_id del registro esta vacio')
    if alumno.Token_tel == '':
              errores.append('El token del registro esta vacio')
    
    errores_contrasena = verificacion_de_contrasenas(alumno)
    errores += errores_contrasena
    return errores

def get_client_ip(request):
    """
    Funcion que permite la optencion de l ip del usuario que se esta conectando al sistema

    Keyword Arguments:
    request --
    returns: str
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def es_ip_conocida(ip: str):
    """
    Funcion que permite saber si a ip ya esta entre las que ya han entrada al sistema 

    Keyword Arguments:
    ip: str
    returns: bool
    """
    registros = models.IntentosIP.objects.filter(ip=ip)
    return len(registros) != 0


def guardar_peticion(ip: str, intentos: int):
    """
    Determina si la ip ya está en la BD.

    Keyword Arguments:
    ip: str
    returns: None
    """
    fecha_actual = datetime.datetime.now()
    if not es_ip_conocida(ip):
        entrada = models.IntentosIP(ip=ip, intentos=1,timestamp=fecha_actual)
        entrada.save()
        return
    registro = models.IntentosIP.objects.get(ip=ip)
    registro.intentos = intentos
    registro.timestamp = fecha_actual
    registro.save()
   
def esta_tiempo_en_ventana(timestamp):
    """
    Funcion que permite saber el tiempo que ha estado en la ventana del navegador    

    Keyword Arguments:
    ip: datatime
    returns: bool
    """
    momento_actual = datetime.datetime.now(timezone.utc)
    resta = momento_actual - timestamp
    if resta.seconds < conf.VENTANA_SEGUNDOS_INTENTOS_PETICION:
        return True
    return False

def puede_hacer_peticion(ip):
    """
    Verdadero si la IP no ha alcanzado el límite de intentos.

    Keyword Arguments:
    ip --
    returns: Bool
    """
    if not es_ip_conocida(ip):
        guardar_peticion(ip, 1)
        return True
    registro = models.IntentosIP.objects.get(ip=ip)
    if not esta_tiempo_en_ventana(registro.timestamp):
        guardar_peticion(ip, 1)
        return True
    else:
        if (registro.intentos + 1) > conf.INTENTOS_MAXIMOS_PETICION:
            guardar_peticion(ip, registro.intentos + 1)
            return False
        else:
            guardar_peticion(ip, registro.intentos + 1)
            return True

def logout(request):
     request.session['logueado'] = False
     return redirect('/login')


logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO,
                    filename='/logweb/resgistros.log', filemode='a')
