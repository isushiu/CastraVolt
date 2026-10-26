"""Local mail capture by default; SMTP is explicit deployment configuration."""
from email.message import EmailMessage
from pathlib import Path
import logging
import os
import smtplib
import ssl
from uuid import uuid4

logger = logging.getLogger('castravolt')


def deliver(settings,email,kind,token):
    message = EmailMessage()
    message['From'] = settings.mail_from
    message['To'] = email
    message['Subject'] = 'Verify your CastraVolt account' if kind=='verify-email' else 'Reset your CastraVolt password'
    link = f'{settings.frontend_url}/{kind}?token={token}'
    message.set_content(f'Open this link to continue:\n\n{link}\n\nIf you did not request this, ignore this message.\n')
    try:
        if settings.mail_mode=='file':
            directory=Path(settings.mail_directory); directory.mkdir(parents=True,exist_ok=True)
            path=directory/f'{uuid4().hex}.eml'
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'w',encoding='utf-8') as handle: handle.write(message.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as server:
                if settings.smtp_starttls: server.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    server.login(settings.smtp_username,settings.smtp_password.get_secret_value())
                server.send_message(message)
    except (OSError,smtplib.SMTPException):
        # Keep public responses generic; don't disclose account existence or tokens.
        logger.error('account_mail_delivery_failed')
