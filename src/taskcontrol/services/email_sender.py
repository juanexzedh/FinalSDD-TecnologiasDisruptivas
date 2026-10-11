import json
import logging

logger = logging.getLogger("taskcontrol.email")


class ConsoleEmailSender:
    """Despacho de correo simulado (clarify/plan 002, Principio V): imprime el enlace en el
    log estructurado en lugar de usar SMTP. `sent` permite verificarlo en pruebas."""

    def __init__(self):
        self.sent = []

    def send_password_reset(self, to, link):
        self.sent.append((to, link))
        logger.info(
            json.dumps(
                {
                    "EMAIL_SIMULADO": True,
                    "para": to,
                    "asunto": "Restablecimiento de contraseña - TaskControl",
                    "enlace": link,
                },
                ensure_ascii=False,
            )
        )
