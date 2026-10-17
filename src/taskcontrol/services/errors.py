class ServiceError(Exception):
    """Base de errores de dominio (no conocen HTTP)."""


class ValidationError(ServiceError):
    def __init__(self, errors):
        self.errors = errors  # {campo: [mensajes]}
        super().__init__("; ".join(m for ms in errors.values() for m in ms))


class DuplicateEmailError(ServiceError):
    pass


class AuthenticationError(ServiceError):
    pass


class NotFoundError(ServiceError):
    pass


class InvalidTransitionError(ServiceError):
    pass


class TaskDeletedError(ServiceError):
    """Se intentó mutar (editar / cambiar estado / reabrir) una tarea eliminada."""


class TaskAlreadyDeletedError(ServiceError):
    """Se intentó eliminar una tarea que ya estaba eliminada."""


class InvalidTokenError(ServiceError):
    """Token de restablecimiento inexistente, usado o expirado."""


class InvalidPriorityError(ValidationError):
    """Prioridad no permitida (debe ser high, medium o low)."""

    def __init__(self, message="Valor de prioridad inválido. Los valores admitidos son: high, medium, low."):
        if isinstance(message, dict):
            super().__init__(message)
        else:
            super().__init__({"priority": [str(message)]})


class DuplicateCategoryNameError(ValidationError):
    """Nombre de categoría duplicado para el mismo usuario (case-insensitive)."""

    def __init__(self, message="Ya posee una categoría con el nombre especificado."):
        if isinstance(message, dict):
            super().__init__(message)
        else:
            super().__init__({"name": [str(message)]})


class CategoryLimitExceededError(ValidationError):
    """Tope máximo de 50 categorías por usuario superado."""

    def __init__(self, message="Ha alcanzado el límite máximo de 50 categorías permitidas por cuenta."):
        if isinstance(message, dict):
            super().__init__(message)
        else:
            super().__init__({"category": [str(message)]})


class CategoryAccessDeniedError(NotFoundError):
    """Categoría inexistente o perteneciente a otro usuario (seguridad IDOR)."""
    pass
