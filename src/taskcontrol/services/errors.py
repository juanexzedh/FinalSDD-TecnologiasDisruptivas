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
