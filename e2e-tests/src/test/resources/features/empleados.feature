# language: es
Característica: Gestión de empleados
  Como administrador del sistema
  Quiero gestionar los empleados
  Para mantener el registro actualizado

  Antecedentes:
    Dado estoy autenticado como administrador

  Escenario: Consultar lista de empleados
    Cuando consulto la lista de empleados
    Entonces la respuesta debe tener código 200
    Y la respuesta debe contener una lista de empleados

  Escenario: Consultar empleado inexistente
    Cuando consulto el empleado con id 999999
    Entonces la respuesta debe tener código 404
