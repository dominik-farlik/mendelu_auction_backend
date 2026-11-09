import logging
from datetime import datetime, timezone, timedelta

import jwt
from fastapi_mail import MessageSchema, MessageType, FastMail, ConnectionConfig

import config
from config import get_settings

settings = config.get_settings()
logger = logging.getLogger(__name__)

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


async def send_auction_winner_email(email: str, product_title: str, price: float, expires_at: datetime, product_id: int):
    deadline_str = expires_at.strftime("%d.%m.%Y v %H:%M")
    body = f"""
    Gratulujeme! Vyhráli jste aukci produktu '{product_title}'.
    Konečná cena: {price} Kč.

    Pro dokončení objednávky prosím uhraďte částku do {deadline_str}.
    
    Instrukce k zaplacení výhry naleznete zde: {get_settings().FRONTEND_URL}/aukce/platba/{product_id}
    
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

def format_czk(amount: float) -> str:
    """1234.0 -> '1 234 Kč', 400.5 -> '400,50 Kč' (desetinná místa jen když nějaká jsou)."""
    text = f"{amount:,.0f}" if float(amount).is_integer() else f"{amount:,.2f}"
    return f"{text.replace(',', ' ').replace('.', ',')} Kč"


async def send_payment_reported_email(
        recipients: list[str],
        product_title: str,
        amount: float,
        variable_symbol: str,
        buyer_name: str,
        buyer_email: str,
        delivery_text: str,
        group_link: str,
):
    """
    Upozorní členy skupiny, že výherce potvrdil platbu a zvolil způsob převzetí.
    Volá se na pozadí, chyba odeslání proto jen zaloguje a potvrzení objednávky neshodí.
    """
    body = f"""
    Dobrý den,

    výherce aukce '{product_title}' právě potvrdil, že zaplatil, a zvolil způsob převzetí.
    Platba by tedy měla být na cestě. Ověřte ji prosím na transparentním účtu podle těchto údajů:

    Variabilní symbol: {variable_symbol}
    Částka: {format_czk(amount)}

    Výherce: {buyer_name} ({buyer_email})
    Způsob převzetí: {delivery_text}

    Jakmile platbu na účtu najdete, potvrďte ji v detailu skupiny v sekci Ukončené nabídky tlačítkem „Potvrdit platbu“:
    {group_link}
    """
    fm = FastMail(connection_config)
    # Každému členovi zvlášť: neplatná adresa jednoho nezablokuje ostatní a členové nevidí cizí adresy.
    for recipient in recipients:
        try:
            message = MessageSchema(
                subject=f"Výherce pravděpodobně zaplatil: {product_title} (VS {variable_symbol})",
                recipients=[recipient],
                body=body,
                subtype=MessageType.plain
            )
            await fm.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send payment reported email for VS {variable_symbol} to {recipient}: {e}")
