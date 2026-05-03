import smtplib
from email.mime.text import MIMEText
from app.config import settings


def send_email(to_email: str, subject: str, body: str) -> bool:
    host = getattr(settings, "smtp_host", "")
    port = int(getattr(settings, "smtp_port", 587) or 587)
    user = getattr(settings, "smtp_user", "")
    password = getattr(settings, "smtp_password", "")
    from_email = getattr(settings, "smtp_from_email", user or "noreply@miniats.local")
    if not host:
        return False
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        if user:
            server.login(user, password)
        server.sendmail(from_email, [to_email], msg.as_string())
    return True
