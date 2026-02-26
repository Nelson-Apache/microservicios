from typing import Dict, Optional, List, Tuple
from app.models.empleado import Empleado


class EmpleadoYaExisteError(Exception):
    """Error lanzado cuando se intenta crear un empleado con un ID o nombre+cargo ya registrado."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EmpleadosDB:
    """
    Clase para gestionar el almacenamiento en memoria de empleados.
    """

    def __init__(self):
        self._empleados: Dict[int, Empleado] = {}

    # ─────────────────────────────────────────
    # Escritura
    # ─────────────────────────────────────────

    def crear_empleado(self, empleado: Empleado) -> Empleado:
        """
        Registra un nuevo empleado en la base de datos.

        Raises:
            EmpleadoYaExisteError: Si el ID ya está registrado o existe un empleado
                                   con el mismo nombre y cargo.
        """
        # Validar ID duplicado
        if empleado.id in self._empleados:
            raise EmpleadoYaExisteError(
                f"Ya existe un empleado con el id {empleado.id}."
            )

        # Validar nombre + cargo duplicado
        nombre_lower = empleado.nombre.strip().lower()
        cargo_lower = empleado.cargo.strip().lower()
        for emp in self._empleados.values():
            if emp.nombre.strip().lower() == nombre_lower and emp.cargo.strip().lower() == cargo_lower:
                raise EmpleadoYaExisteError(
                    f"Ya existe un empleado con el nombre '{empleado.nombre}' y cargo '{empleado.cargo}'."
                )

        self._empleados[empleado.id] = empleado
        return empleado

    # ─────────────────────────────────────────
    # Lectura individual
    # ─────────────────────────────────────────

    def obtener_empleado(self, empleado_id: int) -> Optional[Empleado]:
        """
        Obtiene un empleado por su ID.

        Returns:
            El empleado si existe, None en caso contrario.
        """
        return self._empleados.get(empleado_id)

    def existe_empleado(self, empleado_id: int) -> bool:
        """Verifica si un empleado existe por su ID."""
        return empleado_id in self._empleados

    # ─────────────────────────────────────────
    # Lectura con filtros y paginación
    # ─────────────────────────────────────────

    def obtener_todos_empleados(self) -> List[Empleado]:
        """Obtiene todos los empleados sin filtros ni paginación."""
        return list(self._empleados.values())

    def buscar_empleados(
        self,
        nombre: Optional[str] = None,
        cargo: Optional[str] = None,
        departamento: Optional[str] = None,
        email: Optional[str] = None,
        pagina: int = 1,
        por_pagina: int = 10,
    ) -> Tuple[List[Empleado], int]:
        """
        Busca empleados aplicando filtros opcionales y paginación.

        Args:
            nombre: Filtro parcial (case-insensitive) por nombre.
            cargo: Filtro parcial (case-insensitive) por cargo.
            departamento: Filtro parcial (case-insensitive) por departamento.
            email: Filtro parcial (case-insensitive) por email.
            pagina: Número de página (1-indexed).
            por_pagina: Cantidad de registros por página.

        Returns:
            Tupla (lista_de_empleados_en_pagina, total_de_coincidencias).
        """
        resultados: List[Empleado] = list(self._empleados.values())

        # Aplicar filtros
        if nombre:
            resultados = [e for e in resultados if nombre.lower() in e.nombre.lower()]
        if cargo:
            resultados = [e for e in resultados if cargo.lower() in e.cargo.lower()]
        if departamento:
            resultados = [
                e for e in resultados
                if e.departamento and departamento.lower() in e.departamento.lower()
            ]
        if email:
            resultados = [
                e for e in resultados
                if e.email and email.lower() in e.email.lower()
            ]

        total = len(resultados)

        # Aplicar paginación
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        pagina_resultado = resultados[inicio:fin]

        return pagina_resultado, total


# Instancia global de la base de datos
db = EmpleadosDB()