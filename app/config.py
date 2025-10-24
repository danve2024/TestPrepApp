import os


class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'LI$cb3ds!gwgy2027')
    DEBUG = False

    # SMTP
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '0') or '0')
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASS = os.getenv('SMTP_PASS')
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', '').lower() == 'true'
    SMTP_USE_SSL = os.getenv('SMTP_USE_SSL', '').lower() == 'true'
    MAIL_FROM = os.getenv('MAIL_FROM')


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
