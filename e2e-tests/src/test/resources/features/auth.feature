# language: es
Característica: Autenticación de usuarios
  Como usuario del sistema
  Quiero poder autenticarme y gestionar mi contraseña
  Para acceder a los recursos protegidos

  Escenario: Login exitoso con credenciales válidas
    Dado el servicio de autenticación está disponible
    Cuando inicio sesión con usuario "admin" y contraseña "admin123"
    Entonces la respuesta debe tener código 200
    Y la respuesta debe contener un token de acceso
    Y el token debe tener tipo "bearer"
    Y el rol del usuario debe ser "ADMIN"

  Escenario: Login fallido con contraseña incorrecta
    Dado el servicio de autenticación está disponible
    Cuando inicio sesión con usuario "admin" y contraseña "wrongpassword"
    Entonces la respuesta debe tener código 401

  Escenario: Login fallido con usuario inexistente
    Dado el servicio de autenticación está disponible
    Cuando inicio sesión con usuario "noexiste" y contraseña "cualquiera"
    Entonces la respuesta debe tener código 401

  Escenario: Solicitud de recuperación de contraseña
    Dado el servicio de autenticación está disponible
    Cuando solicito recuperación de contraseña con email "admin@empresa.com"
    Entonces la respuesta debe tener código 200
    Y la respuesta debe contener el mensaje de recuperación

  Escenario: Recuperación con email inexistente (respuesta genérica)
    Dado el servicio de autenticación está disponible
    Cuando solicito recuperación de contraseña con email "noexiste@empresa.com"
    Entonces la respuesta debe tener código 200
    Y la respuesta debe contener el mensaje de recuperación
