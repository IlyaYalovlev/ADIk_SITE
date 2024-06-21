import smtplib
from celery import Celery
from email.mime.text import MIMEText
from email.header import Header
from config import PASSWORD, EMAIL

celery = Celery('tasks', broker='redis://localhost:6379')

@celery.task
def send_email(email: str, msg_text: str):
    login = EMAIL
    password = PASSWORD
    msg = MIMEText(f'{msg_text}', 'plain', 'utf-8')
    msg['Subject'] = Header('Adik_store', 'utf-8')
    msg['From'] = login
    msg['To'] = email

    smtp_server = 'smtp.yandex.ru'
    smtp_port = 587

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(login, password)
            server.sendmail(login, email, msg.as_string())
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")