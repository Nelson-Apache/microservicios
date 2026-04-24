# language: es
Característica: Onboarding de empleados
  Como administrador del sistema
  Quiero registrar nuevos empleados
  Para que automáticamente se creen sus cuentas de usuario

  Antecedentes:
    Dado que estoy autenticado como "ADMIN"

  Escenario: Registro exitoso de empleado
    Cuando registro un empleado con datos válidos
    Entonces la respuesta debe tener código 201
    Y eventualmente el usuario debe existir en auth-service

  Escenario: Empleado puede hacer login después de onboarding
    Cuando registro un empleado
    Y establece su contraseña
    Y hace login
    Entonces la respuesta debe tener código 200

  Escenario: Registro exitoso genera notificación
    Cuando registro un empleado con datos válidos
    Entonces la respuesta debe tener código 201
    Y eventualmente debe existir una notificación de bienvenida

  Escenario: Registro con datos inválidos
    Cuando registro un empleado con departamento inexistente
    Entonces la respuesta debe tener código 400
