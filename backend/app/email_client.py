"""IMAP email client for fetching unread emails."""
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EmailMessage:
    """Represents a single email message."""

    def __init__(self, subject: str, sender: str, date: datetime,
                 body: str, message_id: str):
        self.subject = subject
        self.sender = sender
        self.date = date
        self.body = body
        self.message_id = message_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert email to dictionary."""
        return {
            'subject': self.subject,
            'sender': self.sender,
            'date': self.date.isoformat() if self.date else None,
            'body': self.body,
            'message_id': self.message_id,
        }

    def __repr__(self) -> str:
        """String representation of email."""
        return f"{self.subject} from {self.sender} ({self.date.strftime('%Y-%m-%d %H:%M')})"


class EmailClient:
    """Client for fetching emails via IMAP."""

    def __init__(self, email_address: Optional[str] = None,
                 app_password: Optional[str] = None,
                 imap_server: str = 'imap.gmail.com',
                 imap_port: int = 993):
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = imap_server
        self.imap_port = imap_port

    def set_credentials(self, email_address: str, app_password: str,
                       imap_server: str = 'imap.gmail.com',
                       imap_port: int = 993) -> None:
        """Set or update email credentials."""
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = imap_server
        self.imap_port = imap_port

    def fetch_unread_emails(self, mailbox: str = 'INBOX',
                           limit: int = 3) -> tuple[Optional[List[EmailMessage]], Optional[str]]:
        """
        Fetch unread emails from specified mailbox.

        Args:
            mailbox: Mailbox to check (default: INBOX)
            limit: Maximum number of emails to fetch

        Returns:
            Tuple of (email list, error message)
        """
        if not self.email_address or not self.app_password:
            return None, "Email credentials not configured"

        try:
            logger.info(f"Connecting to {self.imap_server} for {self.email_address}")

            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)

            # Login
            mail.login(self.email_address, self.app_password)

            # Select mailbox
            mail.select(mailbox)

            # Search for unread messages
            status, messages = mail.search(None, 'UNSEEN')

            if status != 'OK':
                mail.logout()
                return None, f"Failed to search for unread emails: {status}"

            # Get message IDs
            message_ids = messages[0].split()

            if not message_ids:
                logger.info("No unread emails found")
                mail.logout()
                return [], None

            # Fetch the most recent unread emails (up to limit)
            emails = []
            # Get the last N message IDs (most recent)
            recent_ids = message_ids[-limit:]

            for msg_id in reversed(recent_ids):  # Reverse to get newest first
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')

                    if status != 'OK':
                        logger.warning(f"Failed to fetch message {msg_id}")
                        continue

                    # Parse email
                    email_message = self._parse_email(msg_data[0][1])
                    if email_message:
                        emails.append(email_message)

                except Exception as e:
                    logger.warning(f"Error parsing email {msg_id}: {e}")
                    continue

            mail.logout()

            logger.info(f"Successfully fetched {len(emails)} unread emails")
            return emails, None

        except imaplib.IMAP4.error as e:
            error = f"IMAP error: {str(e)}"
            logger.error(error)
            return None, error
        except Exception as e:
            error = f"Error fetching emails: {str(e)}"
            logger.error(error, exc_info=True)
            return None, error

    def _parse_email(self, raw_email: bytes) -> Optional[EmailMessage]:
        """Parse raw email data."""
        try:
            msg = email.message_from_bytes(raw_email)

            # Get subject
            subject = self._decode_header(msg.get('Subject', 'No Subject'))

            # Get sender
            sender = self._decode_header(msg.get('From', 'Unknown'))

            # Get date
            date_str = msg.get('Date')
            try:
                date = parsedate_to_datetime(date_str)
                # Ensure timezone-aware
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
            except:
                date = datetime.now(timezone.utc)

            # Get message ID
            message_id = msg.get('Message-ID', '')

            # Get body
            body = self._get_email_body(msg)

            return EmailMessage(subject, sender, date, body, message_id)

        except Exception as e:
            logger.error(f"Error parsing email: {e}", exc_info=True)
            return None

    def _decode_header(self, header: str) -> str:
        """Decode email header."""
        if not header:
            return ''

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                except:
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(str(part))

        return ''.join(decoded_parts)

    def _get_email_body(self, msg) -> str:
        """Extract email body text."""
        body = ''

        if msg.is_multipart():
            # Get text from multipart message
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                # Skip attachments
                if 'attachment' in content_disposition:
                    continue

                if content_type == 'text/plain':
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            body = payload.decode(charset, errors='replace')
                            break
                    except:
                        pass
                elif content_type == 'text/html' and not body:
                    # Fallback to HTML if no plain text found
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            html_body = payload.decode(charset, errors='replace')
                            # Basic HTML stripping (remove tags)
                            import re
                            body = re.sub('<[^<]+?>', '', html_body)
                    except:
                        pass
        else:
            # Get text from single-part message
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
            except:
                body = str(msg.get_payload())

        # Truncate very long bodies
        if len(body) > 1000:
            body = body[:1000] + '...\n[Email truncated for brevity]'

        return body.strip()

    def format_emails_for_llm(self, emails: List[EmailMessage]) -> str:
        """
        Format emails into a human-readable string for the LLM.

        Args:
            emails: List of email messages

        Returns:
            Formatted string describing the emails
        """
        if not emails:
            return "No unread emails in your inbox."

        lines = ["Here are your most recent unread emails:\n"]

        for i, email_msg in enumerate(emails, 1):
            lines.append(f"{i}. From: {email_msg.sender}")
            lines.append(f"   Subject: {email_msg.subject}")
            lines.append(f"   Received: {email_msg.date.strftime('%A, %B %d at %I:%M %p')}")

            # Include a snippet of the body
            body_preview = email_msg.body[:200] if email_msg.body else "[No content]"
            if len(email_msg.body) > 200:
                body_preview += "..."
            lines.append(f"   Preview: {body_preview}")
            lines.append("")  # Blank line between emails

        return "\n".join(lines)

    def check_health(self) -> bool:
        """Check if email connection is working."""
        if not self.email_address or not self.app_password:
            return False

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            mail.logout()
            return True
        except:
            return False


# Global client instance
email_client = EmailClient()
