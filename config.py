MAIL_SERVER = 'smtp.sendgrid.net'
MAIL_PORT = 587
MAIL_LOGIN = 'mail_user'
MAIL_PASSWORD = 'mail_pw'
SENDER = 'gitolite_parser@git.domain.com'

try:
    from config_local import *
except ImportError:
    pass
