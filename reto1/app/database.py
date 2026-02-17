from typing import Dict, Optional, List
from app.models.empleado import Empleado


class EmpleadosDB:
    """
    Clase para gestionar el almacenamiento en memoria de empleados.
    """
    
    def __init__(self):
        self._empleados: Dict[int, Empleado] = {}
    
    def crear_empleado(self, empleado: Empleado) -> Empleado:
        """
        Registra un nuevo empleado en la base de datos.
        
        Args:
            empleado: Instancia del modelo Empleado
            
        Returns:
            El empleado registrado
        """
        self._empleados[empleado.id] = empleado
        return empleado
    
    def obtener_empleado(self, empleado_id: int) -> Optional[Empleado]:
        """
        Obtiene un empleado por su ID.
        
        Args:
            empleado_id: ID del empleado a buscar
            
        Returns:
            El empleado si existe, None en caso contrario
        """
        return self._empleados.get(empleado_id)
    
    def obtener_todos_empleados(self) -> List[Empleado]:
        """
        Obtiene todos los empleados registrados.
        
        Returns:
            Lista de todos los empleados
        """
        return list(self._empleados.values())
    
    def existe_empleado(self, empleado_id: int) -> bool:
        """
        Verifica si un empleado existe en la base de datos.
        
        Args:
            empleado_id: ID del empleado a verificar
            
        Returns:
            True si existe, False en caso contrario
        """
        return empleado_id in self._empleados


# Instancia global de la base de datos
db = EmpleadosDB()
