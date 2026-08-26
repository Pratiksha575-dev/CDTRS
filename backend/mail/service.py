# ==============================================================================
# PZ_26/08 - Central Domain Mail Service & Notification Dispatcher
# Coordinates idempotent inbox synchronization, server attachment storage,
# SHA-256 integrity checksums, and workflow email notifications.
# ==============================================================================

import os
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

import models
import schemas
import crud

from .base import BaseMailProvider, EmailAttachmentDTO, IncomingEmailDTO, OutgoingEmailDTO
from .outlook_provider import OutlookGraphProvider

logger = logging.getLogger("cdtrs.mail.service")


class MailService:
    """
    Central Domain Mail Service for CDTRS.
    Manages incoming mailbox sync, idempotent ingestion, attachment persistence,
    and workflow-state triggered notifications.
    """

    def __init__(self):
        self._providers: Dict[str, BaseMailProvider] = {
            "outlook": OutlookGraphProvider(),
            # Future: "gov_mail": GovernmentNICMailProvider()
        }
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def get_provider(self, channel: str = "outlook") -> BaseMailProvider:
        return self._providers.get(channel.lower()) or self._providers["outlook"]

    def is_configured(self, channel: str = "outlook") -> bool:
        provider = self.get_provider(channel)
        return provider.is_configured()

    def sync_ds_mailbox(self, db: Session, max_count: int = 50) -> schemas.OutlookSyncResponse:
        """
        Synchronizes the DS Outlook mailbox:
        1. Checks configuration.
        2. Retrieves new incoming messages with attachments via Graph API.
        3. Enforces idempotency via external_message_id.
        4. Persists attachments to server filesystem (uploads/<year>/intake_<msg_id>/<file>).
        5. Registers IncomingMessage and Attachment records.
        """
        provider = self.get_provider("outlook")
        if not provider.is_configured():
            return schemas.OutlookSyncResponse(
                status="not_configured",
                synced_count=0,
                ignored_duplicates=0,
                message="Outlook integration is not configured. Please set OUTLOOK_CLIENT_ID, OUTLOOK_CLIENT_SECRET, OUTLOOK_TENANT_ID, and OUTLOOK_MAILBOX in environment variables."
            )

        try:
            incoming_emails = provider.fetch_incoming_emails(max_count=max_count, unread_only=True)
        except Exception as ex:
            logger.error(f"Mail sync exception: {ex}")
            return schemas.OutlookSyncResponse(
                status="error",
                synced_count=0,
                ignored_duplicates=0,
                message=f"Outlook sync failed: {str(ex)}"
            )

        synced_count = 0
        ignored_count = 0
        details: List[dict] = []

        for email in incoming_emails:
            # Idempotency check: Skip if external message ID already stored
            existing = db.query(models.IncomingMessage).filter(
                models.IncomingMessage.external_message_id == email.message_id
            ).first()

            if existing:
                ignored_count += 1
                continue

            # 1. Create IncomingMessage
            inc_msg = models.IncomingMessage(
                source_type=models.SourceType.OUTLOOK,
                external_message_id=email.message_id,
                sender_name=email.sender_name or email.sender_email or "Outlook Dispatch",
                sender_email=email.sender_email,
                subject=email.subject,
                received_at=email.received_at,
                body_reference=email.body_text,
                has_attachments=bool(email.attachments),
                processing_status=models.MessageProcessingStatus.NEW,
                created_at=datetime.now()
            )
            db.add(inc_msg)
            db.commit()
            db.refresh(inc_msg)

            # 2. Persist Attachments
            if email.attachments:
                dest_dir = self.upload_dir / str(datetime.utcnow().year) / f"intake_{inc_msg.id}"
                dest_dir.mkdir(parents=True, exist_ok=True)

                for att in email.attachments:
                    sanitized_name = "".join(c for c in att.filename if c.isalnum() or c in "._- ") or "attachment.pdf"
                    dest_path = dest_dir / sanitized_name
                    with open(dest_path, "wb") as fh:
                        fh.write(att.content_bytes)

                    checksum = hashlib.sha256(att.content_bytes).hexdigest()
                    storage_key = str(dest_path.relative_to(self.upload_dir))

                    db_att = models.Attachment(
                        document_id=None,  # Nullable until canonical document is registered
                        progress_update_id=None,
                        uploaded_by_user_id=1,  # Default system/DS user ID
                        file_name=att.filename,
                        storage_key=storage_key,
                        file_type=att.content_type,
                        file_size=att.size_bytes,
                        checksum=checksum,
                        attachment_type=models.AttachmentType.ORIGINAL,
                        source_message_id=inc_msg.id,
                        created_at=datetime.now()
                    )
                    db.add(db_att)

                db.commit()

            # Mark as read in remote mailbox
            try:
                provider.mark_as_read(email.message_id)
            except Exception:
                pass

            synced_count += 1
            details.append({
                "id": inc_msg.id,
                "subject": inc_msg.subject,
                "sender": inc_msg.sender_email,
                "attachments_count": len(email.attachments)
            })

        msg_text = f"Successfully synced {synced_count} new email(s) from DS Outlook mailbox."
        if ignored_count > 0:
            msg_text += f" ({ignored_count} duplicate(s) skipped)."

        return schemas.OutlookSyncResponse(
            status="success",
            synced_count=synced_count,
            ignored_duplicates=ignored_count,
            message=msg_text,
            details=details
        )

    def resolve_user_email(self, user: models.User) -> Optional[str]:
        """Resolves the authoritative email address for a user according to preferred channel."""
        if not user:
            return None
        pref = (user.preferred_mail_channel or "outlook").lower()
        if pref == "outlook" and user.outlook_email:
            return user.outlook_email
        elif pref == "gov_mail" and user.gov_email:
            return user.gov_email
        return user.email or user.outlook_email or user.gov_email

    def send_workflow_notification(
        self,
        db: Session,
        doc_id: int,
        recipient_user_id: int,
        title: str,
        message: str,
        channel: Optional[str] = None
    ) -> bool:
        """
        Dispatches an outgoing workflow notification email to the responsible user.
        """
        user = db.query(models.User).filter(models.User.id == recipient_user_id).first()
        doc = db.query(models.Document).filter(models.Document.doc_id == doc_id).first()
        if not user or not doc:
            return False

        recipient_email = self.resolve_user_email(user)
        if not recipient_email:
            logger.warning(f"User {user.username} (ID: {user.id}) has no configured email address. Email skipped.")
            return False

        use_channel = channel or user.preferred_mail_channel or "outlook"
        provider = self.get_provider(use_channel)

        if not provider.is_configured():
            logger.info(f"Mail provider '{use_channel}' not configured. Notification logged to database only.")
            return False

        subject = f"[CDTRS] {title} - {doc.reference_no}"
        body_text = f"""Central Document Tracking & Routing System (CDTRS)
-----------------------------------------------------------
Action Notice: {title}
Document Ref : {doc.reference_no}
Title / Subj : {doc.title}
Priority     : {doc.priority.value}
Deadline     : {doc.deadline or 'Not Specified'}
Current Stage: {doc.current_stage.value}

Message / Instructions:
{message}

Please log in to CDTRS to view or process this document.
"""
        body_html = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #E2E8F0; border-radius: 8px;">
  <h2 style="color: #0F172A; margin-bottom: 4px;">CDTRS Official Action Notice</h2>
  <p style="color: #64748B; font-size: 13px; margin-top: 0;">Central Document Tracking & Routing System</p>
  <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 16px 0;" />
  <p style="font-size: 15px; font-weight: 600; color: #1E293B;">{title}</p>
  <table style="width: 100%; font-size: 13px; color: #334155; margin: 16px 0; border-collapse: collapse;">
    <tr><td style="padding: 6px 0; font-weight: 600; width: 140px;">Reference No:</td><td>{doc.reference_no}</td></tr>
    <tr><td style="padding: 6px 0; font-weight: 600;">Title / Subject:</td><td>{doc.title}</td></tr>
    <tr><td style="padding: 6px 0; font-weight: 600;">Priority:</td><td><span style="background: #0F172A; color: white; padding: 2px 8px; border-radius: 4px; font-weight: 600;">{doc.priority.value}</span></td></tr>
    <tr><td style="padding: 6px 0; font-weight: 600;">Deadline:</td><td>{doc.deadline or 'Not Specified'}</td></tr>
    <tr><td style="padding: 6px 0; font-weight: 600;">Workflow Stage:</td><td>{doc.current_stage.value}</td></tr>
  </table>
  <div style="background-color: #F8FAFC; border-left: 4px solid #0F172A; padding: 12px; margin: 16px 0; font-size: 13px; color: #1E293B;">
    <strong>Instructions / Directives:</strong><br/>
    {message}
  </div>
  <p style="font-size: 12px; color: #94A3B8; margin-top: 24px;">This is an automated workflow notification from the CDTRS Institutional Management Server.</p>
</div>
"""

        # Collect canonical document attachments to include in outgoing email
        attachments_to_send: List[EmailAttachmentDTO] = []
        doc_attachments = db.query(models.Attachment).filter(
            models.Attachment.document_id == doc.doc_id
        ).all()

        for att in doc_attachments:
            if att.storage_key:
                att_file_path = self.upload_dir / att.storage_key
                if att_file_path.exists():
                    try:
                        with open(att_file_path, "rb") as fh:
                            raw_bytes = fh.read()
                        attachments_to_send.append(EmailAttachmentDTO(
                            filename=att.file_name or "document.pdf",
                            content_type=att.file_type or "application/pdf",
                            size_bytes=len(raw_bytes),
                            content_bytes=raw_bytes
                        ))
                    except Exception as ex:
                        logger.warning(f"Could not load attachment {att.file_name} for email: {ex}")

        outgoing_dto = OutgoingEmailDTO(
            recipient_email=recipient_email,
            recipient_name=user.full_name,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments_to_send if attachments_to_send else None
        )

        return provider.send_email(outgoing_dto)


mail_service = MailService()
