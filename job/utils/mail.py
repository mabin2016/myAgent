import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from metagpt.config import CONFIG
from metagpt.logs import logger

class EmailSender:
    def __init__(self, smtp_server=CONFIG.SMTP_SERVER, port=CONFIG.SMTP_PORT):
        self.smtp_server = smtp_server
        self.port = port
        self.sender_email = CONFIG.SEND_EMAIL
        self.sender_password = CONFIG.EMAIL_PASSWORD

    def send_email(self, recipient, subject, body, is_html=True):
        # 创建一个 MIMEMultipart 对象
        msg = MIMEMultipart("alternative" if is_html else "plain")
        msg["From"] = self.sender_email
        msg["To"] = recipient
        msg["Subject"] = subject

        # 根据是否为HTML内容设置邮件体
        if is_html:
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))
        # 设置SMTP服务器并发送邮件
        print(self.sender_email, self.sender_password)
        try:
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, msg.as_string())
            logger.info(f"Email sent successfully! send: {self.sender_email} recipient: {recipient}， subject: {subject}， body: {body}")
        except Exception as e:
            logger.error(f"Failed to send email: {e} send: {self.sender_email}  recipient: {recipient}， subject: {subject}， body: {body}")
