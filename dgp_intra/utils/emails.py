import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def send_email(to, subject, body):
    msg = MIMEText(body, 'plain')
    msg['Subject'] = subject
    msg['From'] = os.getenv('MAIL_DEFAULT_SENDER')
    msg['To'] = to

    server = smtplib.SMTP(os.getenv('MAIL_SERVER'), int(os.getenv('MAIL_PORT')))
    server.starttls()
    server.login(os.getenv('MAIL_USERNAME'), os.getenv('MAIL_PASSWORD'))
    server.send_message(msg)
    server.quit()
