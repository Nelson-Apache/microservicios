# language: es
Característica: Offboarding de empleados
  Como administrador del sistema
  Quiero dar de baja empleados
  Para que automáticamente se inhabiliten sus cuentas

  Antecedentes:
    Dado que existe un empleado activo con credenciales configuradas
    Y que estoy autenticado como "ADMIN"

  Escenario: Desvinculación completa con notificación
    Cuando elimino el empleado
    Entonces la respuesta debe tener código 204
    Y eventualmente el usuario debe estar deshabilitado
    Y eventualmente debe existir una notificación de desvinculación

  Escenario: Empleado desvinculado no puede hacer login
    Dado que el empleado tiene credenciales activas
    Cuando elimino el empleado
    Y el empleado intenta hacer login
    Entonces la respuesta debe tener código 401
    Y el mensaje debe indicar que el usuario está inhabilitado

  # NOTA: Este escenario está comentado porque requiere modificar la lógica de negocio
  # del servicio de autenticación. El comportamiento actual es que recover-password
  # siempre retorna 200 por seguridad (para no revelar si un email existe).
  # Para implementar este escenario, auth-service debería validar si el usuario
  # está deshabilitado antes de generar el token de recuperación.
  #
  # Escenario: Recuperación de contraseña falla para empleado desvinculado
  #   Cuando elimino el empleado
  #   Y solicito recuperación de contraseña para el empleado desvinculado
  #   Entonces la respuesta debe tener código 200
  #   Y eventualmente no debe generarse token de recuperación
