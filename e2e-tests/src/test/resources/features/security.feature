# language: es
Característica: Seguridad y control de acceso
  Como sistema de microservicios
  Quiero proteger los recursos con autenticación JWT
  Para que solo usuarios autorizados puedan acceder

  Antecedentes:
    Dado que el sistema está desplegado

  Escenario: Acceso denegado sin token
    Cuando consulto la lista de empleados sin token de autenticación
    Entonces la respuesta debe tener código 401

  Escenario: Acceso con token inválido
    Cuando consulto la lista de empleados con un token inválido
    Entonces la respuesta debe tener código 401

  Escenario: Usuario USER no puede eliminar empleados
    Dado que estoy autenticado como "USER"
    Cuando intento eliminar un empleado
    Entonces la respuesta debe tener código 403

  Escenario: Usuario ADMIN puede eliminar empleados
    Dado que estoy autenticado como "ADMIN"
    Y existe un empleado creado para eliminar
    Cuando elimino un empleado existente
    Entonces la respuesta debe tener código 204
