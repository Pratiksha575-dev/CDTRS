# ==============================================================================
# CDTRS - Intranet / Local Mail Provider (Standard IMAP & SMTP)
# Enables 100% offline, local-network, and government intranet mail synchronization
# without any dependencies on external cloud APIs or public internet.
# ==============================================================================

import os
import ssl
import email
import logging
import imaplib
import smtplib
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseMailProvider, EmailAttachmentDTO, IncomingEmailDTO, OutgoingEmailDTO

logger = logging.getLogger("cdtrs.mail.intranet")


class IntranetMailProvider(BaseMailProvider):
    """
    Standard IMAP/SMTP provider for Local Office Networks, On-Premises Exchange,
    Government NIC Mail servers, or internal mail daemons (Postfix/Dovecot/hMailServer).
    Operates 100% locally over LAN without internet connection.
    """

    def __init__(self):
        # IMAP Configuration (Incoming Mail Sync)
        self.imap_host = os.getenv("INTRANET_IMAP_HOST", "").strip()
        self.imap_port = int(os.getenv("INTRANET_IMAP_PORT", "993"))
        self.imap_use_ssl = os.getenv("INTRANET_IMAP_SSL", "true").lower() in ("true", "1", "yes")

        # SMTP Configuration (Outgoing Reminders & Notifications)
        self.smtp_host = os.getenv("INTRANET_SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("INTRANET_SMTP_PORT", "587"))
        self.smtp_use_ssl = os.getenv("INTRANET_SMTP_SSL", "false").lower() in ("true", "1", "yes")
        self.smtp_use_starttls = os.getenv("INTRANET_SMTP_STARTTLS", "true").lower() in ("true", "1", "yes")

        # Credentials & Sender Info
        self.username = os.getenv("INTRANET_MAIL_USER", "").strip()
        self.password = os.getenv("INTRANET_MAIL_PASS", "").strip()
        self.sender_address = os.getenv("INTRANET_SENDER_EMAIL", self.username).strip()
        self.sender_name = os.getenv("INTRANET_SENDER_NAME", "CDTRS Directorate Secretary").strip()

    def is_configured(self) -> bool:
        """Returns True if the intranet server host and user are configured."""
        return bool(self.imap_host and self.smtp_host and self.username)

    # --------------------------------------------------------------------------
    # INCOMING MAIL SYNC (IMAP)
    # --------------------------------------------------------------------------

    def _connect_imap(self) -> Optional[imaplib.IMAP4]:
        try:
            if self.imap_use_ssl:
                context = ssl.create_default_context()
                # For intranet self-signed certificates, allow insecure mode if configured
                if os.getenv("INTRANET_ALLOW_SELFSIGNED", "false").lower() in ("true", "1", "yes"):
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                client = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=context)
            else:
                client = imaplib.IMAP4(self.imap_host, self.imap_port)

            if self.username and self.password:
                client.login(self.username, self.password)
            return client
        except Exception as ex:
            logger.error(f"Failed to connect to Intranet IMAP server ({self.imap_host}:{self.imap_port}): {ex}")
            return None

    def fetch_incoming_emails(
        self,
        max_count: int = 50,
        unread_only: bool = True
    ) -> List[IncomingEmailDTO]:
        """
        Fetches incoming emails and attachments from the local intranet inbox via IMAP.
        """
        if not self.is_configured():
            logger.info("Intranet mail provider is not configured. Skipping IMAP sync.")
            return []

        client = self._connect_imap()
        if not client:
            return []

        results: List[IncomingEmailDTO] = []
        try:
            client.select("INBOX")
            search_crit = "UNSEEN" if unread_only else "ALL"
            status, msg_nums = client.search(None, search_crit)
            if status != "OK" or not msg_nums[0]:
                return []

            num_list = msg_nums[0].split()
            # Most recent first, capped at max_count
            num_list = num_list[-max_count:][::-1]

            for num in num_list:
                try:
                    res, data = client.fetch(num, "(RFC822)")
                    if res != "OK" or not data or not isinstance(data[0], tuple):
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # 1. Parse Subject
                    subject_header = msg.get("Subject", "(No Subject)")
                    subject = self._decode_header_str(subject_header)

                    # 2. Parse Sender
                    from_header = msg.get("From", "")
                    sender_name, sender_email = self._parse_from_header(from_header)

                    # 3. Message ID
                    msg_id = msg.get("Message-ID", f"intranet-{num.decode('utf-8')}-{int(datetime.now().timestamp())}")
                    msg_id = msg_id.strip("<>").strip()

                    # 4. Date
                    date_header = msg.get("Date")
                    received_at = datetime.now()
                    if date_header:
                        try:
                            parsed_date = email.utils.parsedate_to_datetime(date_header)
                            if parsed_date:
                                received_at = parsed_date.replace(tzinfo=None)
                        except Exception:
                            pass

                    # 5. Extract Body & Attachments
                    body_text = ""
                    body_html = ""
                    attachments: List[EmailAttachmentDTO] = []

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition", ""))
                            filename = part.get_filename()

                            if filename:
                                filename = self._decode_header_str(filename)
                                file_bytes = part.get_payload(decode=True)
                                if file_bytes:
                                    attachments.append(EmailAttachmentDTO(
                                        filename=filename,
                                        content_type=content_type or "application/octet-stream",
                                        size_bytes=len(file_bytes),
                                        content_bytes=file_bytes
                                    ))
                            elif "attachment" in content_disposition:
                                file_bytes = part.get_payload(decode=True)
                                if file_bytes:
                                    attachments.append(EmailAttachmentDTO(
                                        filename="attachment.pdf",
                                        content_type=content_type or "application/pdf",
                                        size_bytes=len(file_bytes),
                                        content_bytes=file_bytes
                                    ))
                            elif content_type == "text/plain" and not body_text:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body_text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                            elif content_type == "text/html" and not body_html:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body_html = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    else:
                        content_type = msg.get_content_type()
                        payload = msg.get_payload(decode=True)
                        if payload:
                            decoded = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
                            if content_type == "text/html":
                                body_html = decoded
                            else:
                                body_text = decoded

                    dto = IncomingEmailDTO(
                        message_id=msg_id,
                        sender_name=sender_name or "Intranet User",
                        sender_email=sender_email or "intranet@office.lan",
                        subject=subject,
                        body_text=body_text or None,
                        body_html=body_html or None,
                        received_at=received_at,
                        has_attachments=len(attachments) > 0,
                        attachments=attachments
                    )
                    results.append(dto)

                except Exception as ex:
                    logger.warning(f"Error parsing intranet email item #{num}: {ex}")

        except Exception as ex:
            logger.error(f"Error during Intranet IMAP fetch: {ex}")
        finally:
            try:
                client.close()
                client.logout()
            except Exception:
                pass

        return results

    def mark_as_read(self, message_id: str) -> bool:
        """Marks email as read via IMAP flag."""
        # Standard IMAP marks as read during RFC822 fetch by default
        return True

    # --------------------------------------------------------------------------
    # OUTGOING MAIL DISPATCH (SMTP)
    # --------------------------------------------------------------------------

    def send_email(self, email_dto: OutgoingEmailDTO) -> bool:
        """
        Dispatches an email across the intranet mail server via standard SMTP.
        """
        if not self.is_configured():
            logger.warning("Intranet SMTP is not configured. Email dispatch skipped.")
            return False

        try:
            msg = MIMEMultipart("mixed")
            msg["From"] = f"{self.sender_name} <{self.sender_address}>"
            msg["To"] = f"{email_dto.recipient_name} <{email_dto.recipient_email}>"
            msg["Subject"] = email_dto.subject
            msg["Date"] = email.utils.formatdate(localtime=True)

            # Alternate container for text & HTML
            alt_part = MIMEMultipart("alternative")
            if email_dto.body_text:
                alt_part.attach(MIMEText(email_dto.body_text, "plain", "utf-8"))
            if email_dto.body_html:
                alt_part.attach(MIMEText(email_dto.body_html, "html", "utf-8"))
            msg.attach(alt_part)

            # Attachments
            if email_dto.attachments:
                for att in email_dto.attachments:
                    part = MIMEApplication(att.content_bytes, Name=att.filename)
                    part["Content-Disposition"] = f'attachment; filename="{att.filename}"'
                    msg.attach(part)

            # Connect SMTP
            if self.smtp_use_ssl:
                context = ssl.create_default_context()
                if os.getenv("INTRANET_ALLOW_SELFSIGNED", "false").lower() in ("true", "1", "yes"):
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
                if self.smtp_use_starttls:
                    context = ssl.create_default_context()
                    if os.getenv("INTRANET_ALLOW_SELFSIGNED", "false").lower() in ("true", "1", "yes"):
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                    server.starttls(context=context)

            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.sender_address, [email_dto.recipient_email], msg.as_string())
            server.quit()
            logger.info(f"Intranet email successfully delivered to {email_dto.recipient_email} via SMTP ({self.smtp_host})")
            return True

        except Exception as ex:
            logger.error(f"Failed to send email via Intranet SMTP ({self.smtp_host}:{self.smtp_port}): {ex}")
            return False

    # --------------------------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------------------------

    @staticmethod
    def _decode_header_str(header_str: str) -> str:
        if not header_str:
            return ""
        decoded_fragments = decode_header(header_str)
        text_parts = []
        for text, encoding in decoded_fragments:
            if isinstance(text, bytes):
                try:
                    text_parts.append(text.decode(encoding or "utf-8", errors="replace"))
                except Exception:
                    text_parts.append(text.decode("latin1", errors="replace"))
            else:
                text_parts.append(str(text))
        return "".join(text_parts)

    @staticmethod
    def _parse_from_header(from_header: str) -> tuple:
        if not from_header:
            return ("", "")
        name, addr = email.utils.parseaddr(from_header)
        return (name, addr)
