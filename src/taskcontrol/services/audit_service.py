import json
import logging
from datetime import datetime, timezone

from ..extensions import db
from ..models import AuditLog

logger = logging.getLogger("taskcontrol.audit")


def record_event(actor_id, action, entity_type, entity_id, details=None):
    """Único punto de registro de auditoría (Principio VIII). No hace commit:
    participa en la transacción del servicio que lo invoca."""
    now = datetime.now(timezone.utc)
    entry = AuditLog(
        timestamp=now,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details, ensure_ascii=False) if details else None,
    )
    db.session.add(entry)
    logger.info(
        json.dumps(
            {
                "timestamp": now.isoformat(),
                "actor_id": actor_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details,
            },
            ensure_ascii=False,
        )
    )
    return entry


def record_task_event(actor_id, action, task_id, details=None):
    return record_event(actor_id, action, "Task", task_id, details)
