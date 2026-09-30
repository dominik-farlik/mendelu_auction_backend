from datetime import datetime, timezone, timedelta

import jwt
from fastapi_mail import MessageSchema, MessageType, FastMail, ConnectionConfig

import config


settings = config.get_settings()

connection_config = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )


def create_verification_token(email: str, settings: config.Settings):
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {"sub": email, "type": "email_verification", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.PASSWORD_ALGORITHM)


async def send_verification_email(email: str, verification_link: str):
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

    fm = FastMail(connection_config)
    await fm.send_message(message)


async def send_password_reset_email(email: str, password_reset_link: str):
    body = f"Pro obnovení hesla klikněte na tento odkaz (platnost 30 minut):\n{password_reset_link}"

    message = MessageSchema(
        subject="Obnovení zapomenutého hesla",
        recipients=[email],
        body=body,
        subtype=MessageType.plain
    )

    fm = FastMail(connection_config)
    await fm.send_message(message)


async def send_auction_winner_email(email: str, product_title: str, price: float, expires_at: datetime):
    deadline_str = expires_at.strftime("%d.%m.%Y v %H:%M")
    body = f"""
    Gratulujeme! Vyhráli jste aukci produktu '{product_title}'.
    Konečná cena: {price} Kč.

    Pro dokončení objednávky prosím uhraďte částku do {deadline_str}.
    Pokud platba nebude provedena, nabídka automaticky přejde na dalšího dražitele v pořadí.
    """
    message = MessageSchema(
        subject="Vyhráli jste aukci! Instrukce k platbě",
        recipients=[email],
        body=body,
        subtype=MessageType.plain
    )
    fm = FastMail(connection_config)
    await fm.send_message(message)


async def send_runner_up_email(email: str, product_title: str, price: float, expires_at: datetime):
    deadline_str = expires_at.strftime("%d.%m.%Y v %H:%M")
    body = f"""
    Dobrý den, původní výherce aukce produktu '{product_title}' neuhradil platbu včas. 
    Jelikož jste byl/a dalším v pořadí s nabídkou {price} Kč, produkt nyní nabízíme vám!

    Máte 48 hodin (do {deadline_str}) na uhrazení částky a převzetí produktu.
    """
    message = MessageSchema(
        subject="Dodatečná nabídka: Vyhráli jste aukci!",
        recipients=[email],
        body=body,
        subtype=MessageType.plain
    )
    fm = FastMail(connection_config)
    await fm.send_message(message)