import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de entorno desde .env

def send_summary_email(to_email: str, summary_text: str) -> bool:
    """
    Envía un correo con el resumen de la conversación.
    
    Args:
        to_email (str): Correo electrónico del destinatario.
        summary_text (str): Texto del resumen a enviar.
    
    Returns:
        bool: True si el envío fue exitoso, False en caso contrario.
    """
    try:
        # Configuración del mensaje
        msg = MIMEMultipart()
        msg['From'] = os.getenv('SMTP_USERNAME')
        msg['To'] = to_email
        msg['Subject'] = "Resumen de tu Conversación"
        
        # Cuerpo del correo
        msg.attach(MIMEText(summary_text, 'plain'))
        
        # Configuración del servidor SMTP
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False