from datetime import datetime, timezone, timedelta

import jwt
from fastapi_mail import MessageSchema, MessageType, FastMail, ConnectionConfig

import config


settings = config.get_settings()


def create_verification_token(email: str, settings: config.Settings):
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {"sub": email, "type": "email_verification", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.PASSWORD_ALGORITHM)


async def send_verification_email(email: str, verification_link: str):
    # Obsah e-mailu. Později sem můžeš vložit hezkou HTML šablonu.
    body = f"""
    Dobrý den,
    děkujeme za registraci. Pro ověření vašeho e-mailu klikněte na následující odkaz:

    {verification_link}

    Pokud jste se neregistrovali, můžete tento e-mail ignorovat.
    """

    message = MessageSchema(
        subject="Ověření e-mailové adresy",
        recipients=[email],
        body=body,
        subtype=MessageType.plain
    )

    fm = FastMail(ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
))
    await fm.send_message(message)