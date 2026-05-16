# language: es
Característica: Gestión de vacaciones
  Como administrador del sistema
  Quiero programar vacaciones para los empleados
  Para que sus accesos se gestionen automáticamente según las fechas

  Antecedentes:
    Dado que existe un empleado activo con credenciales configuradas
    Y que estoy autenticado como "ADMIN"

  Escenario: Programar vacaciones exitosamente
    Cuando programo vacaciones para el empleado
    Entonces la respuesta debe tener código 201

  Escenario: Consultar vacaciones por empleado
    Dado que el empleado ya tiene vacaciones programadas
    Cuando consulto las vacaciones del empleado
    Entonces la respuesta debe tener código 200
    Y la respuesta debe contener la lista de vacaciones

  Escenario: No se permiten solapamientos de períodos
    Dado que el empleado ya tiene vacaciones programadas
    Cuando programo vacaciones que se solapan para el mismo empleado
    Entonces la respuesta debe tener código 409

  Escenario: Cuenta desactivada al programar vacaciones
    Cuando programo vacaciones para el empleado
    Entonces la respuesta debe tener código 201
    Y eventualmente la cuenta del empleado debe estar desactivada por vacaciones

  Escenario: Cuenta reactivada al finalizar vacaciones
    Dado que el empleado ya tiene vacaciones programadas
    Cuando finalizo las vacaciones del empleado
    Entonces la respuesta debe tener código 200
    Y eventualmente la cuenta del empleado debe estar reactivada
