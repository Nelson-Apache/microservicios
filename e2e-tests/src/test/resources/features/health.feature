# language: es
Característica: Verificación del sistema
  Como operador del sistema
  Quiero verificar que todos los servicios responden correctamente
  Para asegurar que el sistema está operativo

  Escenario: El sistema responde correctamente
    Dado que el sistema está desplegado y operativo
    Entonces la respuesta debe tener código 200
