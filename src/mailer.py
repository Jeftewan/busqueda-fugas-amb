import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from src.utils import load_config


def enviar_correo(asunto: str, cuerpo_html: str,
                  adjunto_pdf: bytes = None, adjunto_nombre: str = "reporte.pdf") -> tuple:
    config = load_config()
    smtp_cfg = config.get("smtp", {})

    host = smtp_cfg.get("host", "smtp.gmail.com")
    port = smtp_cfg.get("port", 587)
    user = smtp_cfg.get("user", "")
    password = smtp_cfg.get("password", "")
    remitente_nombre = smtp_cfg.get("remitente_nombre", "Seguimiento Fugas")
    destinatario = config.get("destinatarios", {}).get("fijo", "")

    if not user or not password:
        return False, "SMTP no configurado. Configure usuario y contraseña en Configuración."
    if not destinatario:
        return False, "Destinatario no configurado. Configure en Configuración."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = f"{remitente_nombre} <{user}>"
        msg["To"] = destinatario

        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        if adjunto_pdf:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(adjunto_pdf)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{adjunto_nombre}"')
            msg.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(user, password)
            server.sendmail(user, destinatario, msg.as_string())

        return True, f"Correo enviado a {destinatario}"

    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticación SMTP. Verifique usuario y App Password."
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {e}"
    except Exception as e:
        return False, f"Error inesperado: {e}"
