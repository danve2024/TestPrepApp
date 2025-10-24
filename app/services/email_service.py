import os
import smtplib
import ssl
from email.message import EmailMessage


def send_email_plain(to_email: str, subject: str, body: str) -> bool:
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '0') or '0')
    user = os.getenv('SMTP_USER')
    pwd = os.getenv('SMTP_PASS')
    mail_from = os.getenv('MAIL_FROM') or (user or 'no-reply@example.com')
    use_tls = os.getenv('SMTP_USE_TLS', '').lower() == 'true'
    use_ssl = os.getenv('SMTP_USE_SSL', '').lower() == 'true'

    msg = EmailMessage()
    msg['From'] = mail_from
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.set_content(body)

    def _send_via(hostname: str, portnum: int, tls: bool, ssl_on: bool, usern: str, pwdn: str) -> None:
        if ssl_on:
            with smtplib.SMTP_SSL(hostname, portnum, context=ssl.create_default_context(), timeout=10) as s:
                if usern and pwdn:
                    s.login(usern, pwdn)
                s.send_message(msg)
        else:
            with smtplib.SMTP(hostname, portnum, timeout=10) as s:
                if tls:
                    s.starttls(context=ssl.create_default_context())
                if usern and pwdn:
                    s.login(usern, pwdn)
                s.send_message(msg)

    attempts = []
    if host and port:
        attempts.append((host, port, use_tls if (use_tls or use_ssl) else True, use_ssl, user, pwd, 'env-primary'))
    if (user and '@gmail.com' in user.lower()) or (mail_from and '@gmail.com' in mail_from.lower()):
        attempts.append(('smtp.gmail.com', 587, True, False, user, pwd, 'gmail-tls-587'))
        attempts.append(('smtp.gmail.com', 465, False, True, user, pwd, 'gmail-ssl-465'))
    attempts.append(('localhost', 1025, False, False, None, None, 'dev-mailpit'))

    last_err = None
    for h, p, tls, ssl_on, u, pw, label in attempts:
        try:
            if not h or not p:
                continue
            if ('gmail' in label) and (not u or not pw):
                print('[email] Gmail selected but SMTP_USER/SMTP_PASS not set. Generate an App Password in Google Account > Security.')
                continue
            _send_via(h, p, tls, ssl_on, u, pw)
            print(f"[email] sent via {label} {h}:{p} tls={tls} ssl={ssl_on}")
            return True
        except Exception as e:
            last_err = e
            print(f"[email] attempt {label} failed via {h}:{p} (tls={tls}, ssl={ssl_on}): {e}")
            continue
    print(f"[email] all attempts failed. Last error: {last_err}")
    return False
