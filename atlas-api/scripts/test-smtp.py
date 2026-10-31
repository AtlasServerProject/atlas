#!/usr/bin/env python3
"""Validate SMTP; --send explicitly sends one fixed test message to the Atlas sender itself."""
import argparse
from email.message import EmailMessage
from pathlib import Path
import smtplib
import ssl

parser=argparse.ArgumentParser()
parser.add_argument('--send',action='store_true',help='Send one test email to the configured Atlas sender')
args=parser.parse_args()
config={}
for line in (Path(__file__).resolve().parents[1]/'.env').read_text().splitlines():
    if line and not line.lstrip().startswith('#') and '=' in line:
        key,value=line.split('=',1);config[key]=value
password=config.get('ATLAS_SMTP_PASSWORD','')
if not password or any(char.isspace() for char in password):
    raise SystemExit('Configure the app password without spaces in the private environment file.')
try:
    with smtplib.SMTP(config['ATLAS_SMTP_HOST'],int(config.get('ATLAS_SMTP_PORT','587')),timeout=15) as smtp:
        smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
        smtp.login(config['ATLAS_SMTP_USERNAME'],password)
        if args.send:
            message=EmailMessage()
            message['From']=config['ATLAS_MAIL_FROM'];message['To']=config['ATLAS_MAIL_FROM']
            message['Subject']='Atlas Cobblemon — teste de envio'
            message.set_content('Este é um teste de envio de email do backend Atlas Cobblemon.\n\nA conexão com o Gmail foi autenticada. Este email não contém links, senhas ou códigos.\n')
            smtp.send_message(message)
            print('Test message accepted by SMTP; check the Atlas mailbox for delivery.')
        else:
            print('SMTP authentication successful; no email sent.')
except Exception as error:
    raise SystemExit('SMTP test failed ('+type(error).__name__+'); credentials suppressed.') from None
