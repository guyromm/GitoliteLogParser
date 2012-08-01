"""
Send email
"""
import smtplib
from config import MAIL_SERVER, MAIL_PORT, MAIL_LOGIN, MAIL_PASSWORD, SENDER
from email.MIMEMultipart import MIMEMultipart
from email.Utils import COMMASPACE, formatdate
from email.header import Header
from email.mime.text import MIMEText


class MailMan(object):
    def __init__(self, recipients, server=MAIL_SERVER, port=MAIL_PORT,
                 login=MAIL_LOGIN, password=MAIL_PASSWORD):
        self.server = server
        self.port = port
        self.login = login
        self.password = password
        self.recipients = recipients
        self.sender = SENDER

    @staticmethod
    def mail_send(self, subject, message):
        assert type(self.recipients) == list
        #msg = MIMEText(message, "", "utf-8")
        msg = MIMEMultipart('related')
        msg['From'] = Header(self.sender.decode("utf-8")).encode()
        msg['To'] = Header(COMMASPACE.join(self.recipients)
                                     .decode("utf-8")).encode()
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = Header(subject.decode("utf-8")).encode()
        msg.preamble = 'This is a multi-part message in MIME format.'
        msgAlternative = MIMEMultipart('alternative')
        msg.attach(msgAlternative)
        msgText = MIMEText(str(message))
        msgAlternative.attach(msgText)
        msgText = MIMEText('<pre>%s</pre>' % message, 'html')
        msgAlternative.attach(msgText)
        server = smtplib.SMTP(self.server, self.port)
        server.starttls()
        server.login(self.login, self.password)
        if 'example.com' not in ''.join(self.recipients):
            server.sendmail(self.sender, self.recipients, msg.as_string())
        server.quit()
