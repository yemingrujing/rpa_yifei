from typing import Any, Dict, Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from .base import BaseComponent, ComponentType


class EmailComponent(BaseComponent):
    def __init__(self, component_id: str, action: str = "send"):
        super().__init__(component_id, ComponentType.EMAIL, f"Email_{action}")
        self.action = action
        self.category = "通信"
        self.description = f"执行邮件{action}操作"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.action == "send":
            if not self.get_property('smtp_server'):
                return False, "smtp_server is required"
            if not self.get_property('sender'):
                return False, "sender email is required"
            if not self.get_property('recipient'):
                return False, "recipient is required"
        return True, None

    def execute(self, context: Any) -> Any:
        if self.action == "send":
            return self._send_email(context)
        elif self.action == "receive":
            return self._receive_email(context)
        elif self.action == "download_attachment":
            return self._download_attachment(context)
        
        return {}

    def _resolve_variable(self, value: Any, context: Any) -> Any:
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            var_name = value[2:-1]
            return context.get('variables', {}).get(var_name, value)
        return value

    def _send_email(self, context: Any) -> Dict[str, Any]:
        smtp_server = self._resolve_variable(self.get_property('smtp_server'), context)
        smtp_port = self.get_property('smtp_port', 465)
        use_ssl = self.get_property('use_ssl', True)
        
        sender = self._resolve_variable(self.get_property('sender'), context)
        password = self._resolve_variable(self.get_property('password'), context)
        
        recipient = self._resolve_variable(self.get_property('recipient'), context)
        if isinstance(recipient, str):
            recipient = [r.strip() for r in recipient.split(',')]
        
        subject = self._resolve_variable(self.get_property('subject'), context)
        body = self._resolve_variable(self.get_property('body'), context)
        
        body_type = self.get_property('body_type', 'plain')
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ', '.join(recipient)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, body_type))
        
        attachments = self.get_property('attachments', [])
        if isinstance(attachments, str):
            attachments = [attachments]
        
        for attachment_path in attachments:
            attachment_path = self._resolve_variable(attachment_path, context)
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(attachment_path)
                part.add_header('Content-Disposition', f'attachment; filename={filename}')
                msg.attach(part)
        
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
            
            if password:
                server.login(sender, password)
            
            server.send_message(msg)
            server.quit()
            
            return {
                'success': True,
                'recipient': recipient,
                'subject': subject
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _receive_email(self, context: Any) -> Dict[str, Any]:
        imap_server = self._resolve_variable(self.get_property('imap_server'), context)
        imap_port = self.get_property('imap_port', 993)
        
        email = self._resolve_variable(self.get_property('email'), context)
        password = self._resolve_variable(self.get_property('password'), context)
        
        folder = self.get_property('folder', 'INBOX')
        limit = self.get_property('limit', 10)
        
        try:
            import imaplib
            server = imaplib.IMAP4_SSL(imap_server, imap_port)
            server.login(email, password)
            server.select(folder)
            
            search_criteria = self.get_property('search_criteria', 'ALL')
            _, message_ids = server.search(None, search_criteria)
            
            email_ids = message_ids[0].split()[-limit:]
            
            emails = []
            for email_id in email_ids:
                _, msg_data = server.fetch(email_id, '(RFC822)')
                emails.append({
                    'id': email_id.decode() if isinstance(email_id, bytes) else email_id,
                    'data': str(msg_data[0])
                })
            
            server.close()
            server.logout()
            
            output_var = self.get_property('output_variable', 'emails')
            context['variables'][output_var] = emails
            
            return {
                'success': True,
                'count': len(emails),
                'emails': emails
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _download_attachment(self, context: Any) -> Dict[str, Any]:
        save_dir = self._resolve_variable(self.get_property('save_dir'), context)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        return {
            'success': True,
            'saved_to': save_dir
        }


class EmailSendComponent(EmailComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "send")
        self.category = "通信"
        self.description = "发送电子邮件"


class EmailReceiveComponent(EmailComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "receive")
        self.category = "通信"
        self.description = "接收电子邮件"
