"""Read separation mail and send the MIS summary through Outlook COM."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger("separation")

# olMailItem, olFolderInbox, olMail
OL_MAIL_ITEM = 0
OL_FOLDER_INBOX = 6
OL_MAIL_CLASS = 43

WORD_EXTENSIONS = {".doc", ".docx", ".docm"}


class MailError(Exception):
    """An Outlook message could not be read or updated."""


def connect():
    """Attach to Outlook, starting it only when it is not already running."""
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 is required. Run this script on the Windows PC where Outlook is installed."
        ) from exc
    try:
        return win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        return win32com.client.Dispatch("Outlook.Application")


def pending_messages(app, config: dict) -> list:
    """Return unread separation messages that are not already categorized as filed."""
    namespace = app.GetNamespace("MAPI")
    outlook_config = config["outlook"]
    folder = open_folder(namespace, outlook_config["mailbox"], outlook_config["folder_path"])
    _reject_unfiltered_inbox(namespace, folder, outlook_config["subject_contains"])
    items = _unread_items(folder)
    category = outlook_config["processed_category"]
    needle = outlook_config["subject_contains"].casefold()
    matched = []
    count = int(items.Count)
    for index in range(1, count + 1):
        try:
            item = items.Item(index)
        except Exception:
            logger.warning("Skipped an Outlook item that could not be read.", exc_info=True)
            continue
        try:
            if not _is_mail(item) or not _is_unread(item):
                continue
            if category and _has_category(item, category):
                continue
            subject = subject_of(item)
            if needle and needle not in subject.casefold():
                continue
        except Exception:
            logger.warning("Skipped an Outlook item that could not be read.", exc_info=True)
            continue
        matched.append(item)
    return matched


def open_folder(namespace, mailbox: str, folder_path: str):
    """Walk a mailbox path such as Inbox\\Separation. An empty path is the Inbox."""
    if mailbox:
        current = namespace.Folders.Item(mailbox)
    else:
        current = namespace.GetDefaultFolder(OL_FOLDER_INBOX).Parent
    parts = [part for part in re.split(r"[\\/]+", folder_path or "") if part]
    if not parts:
        if mailbox:
            return current.Folders.Item("Inbox")
        return namespace.GetDefaultFolder(OL_FOLDER_INBOX)
    for part in parts:
        current = current.Folders.Item(part)
    return current


def subject_of(message) -> str:
    return str(getattr(message, "Subject", "") or "")


def describe(message) -> str:
    """One dry-run line: received time, subject, and attachment names."""
    received = getattr(message, "ReceivedTime", "")
    names = []
    attachments = message.Attachments
    for index in range(1, int(attachments.Count) + 1):
        names.append(str(attachments.Item(index).FileName))
    listed = ", ".join(names) if names else "(none)"
    return f"{received} | {subject_of(message)} | attachments: {listed}"


def save_word_attachment(message, directory: Path) -> Path:
    """Save the single Word attachment. Signature pictures are ignored."""
    found = []
    attachments = message.Attachments
    for index in range(1, int(attachments.Count) + 1):
        attachment = attachments.Item(index)
        file_name = str(attachment.FileName or "")
        if file_name.startswith("~$"):
            continue
        if Path(file_name).suffix.lower() in WORD_EXTENSIONS:
            found.append(attachment)
    if not found:
        raise MailError("The message has no Word attachment (.doc, .docx, or .docm).")
    if len(found) > 1:
        raise MailError("The message has more than one Word attachment.")
    suffix = Path(str(found[0].FileName)).suffix.lower()
    target = Path(directory) / f"attachment{suffix}"
    found[0].SaveAsFile(str(target))
    if not target.is_file():
        raise MailError(f"Outlook did not save the Word attachment to {target}.")
    return target


def mark_processed(message, app, config: dict) -> None:
    """Mark the message read and categorized, then move it when configured.

    The category is saved before the optional move, so a failed move still
    keeps the message out of the next run.
    """
    category = config["outlook"]["processed_category"]
    if category and not _has_category(message, category):
        existing = [
            part.strip()
            for part in str(getattr(message, "Categories", "") or "").split(",")
            if part.strip()
        ]
        existing.append(category)
        message.Categories = ", ".join(existing)
    message.UnRead = False
    message.Save()
    folder_path = config["outlook"]["processed_folder"]
    if not folder_path:
        return
    try:
        namespace = app.GetNamespace("MAPI")
        destination = open_folder(namespace, config["outlook"]["mailbox"], folder_path)
        message.Move(destination)
    except Exception as exc:
        logger.warning(
            "The message was marked processed, and it could not be moved to %s: %s",
            folder_path,
            exc,
        )


def build_summary_body(filed: list[dict], failed: list[dict]) -> str:
    """Plain-text MIS summary: name, form number, last working day, and PDF path."""
    lines = ["Separation forms filed", ""]
    if not filed:
        lines.append("None.")
        lines.append("")
    for index, row in enumerate(filed, 1):
        lines.append(f"{index}. Staff name: {row['staff_name']}")
        lines.append(f"   Form no: {row['form_no']}")
        lines.append(f"   Last working day: {row['last_working_day']}")
        lines.append(f"   PDF: {row['pdf_path']}")
        if row.get("mark_error"):
            lines.append(f"   Mark processed failed: {row['mark_error']}")
        lines.append("")
    if failed:
        lines.append("Not filed")
        lines.append("")
        for index, row in enumerate(failed, 1):
            lines.append(f"{index}. Subject: {row['subject']}")
            lines.append(f"   Error: {row['error']}")
            lines.append("")
    return "\r\n".join(lines).rstrip() + "\r\n"


def send_summary(app, config: dict, body: str) -> None:
    """Send one mail to the MIS distribution list."""
    mail = app.CreateItem(OL_MAIL_ITEM)
    mail.To = "; ".join(config["summary_mail"]["to"])
    cc = config["summary_mail"]["cc"]
    if cc:
        mail.CC = "; ".join(cc)
    mail.Subject = config["summary_mail"]["subject"] or "Separation forms filed"
    mail.Body = body
    mail.Send()


def _unread_items(folder):
    items = folder.Items
    try:
        return items.Restrict("[UnRead] = true")
    except Exception:
        logger.warning("Outlook could not filter unread items; checking each item.")
        return items


def _is_mail(item) -> bool:
    try:
        return int(item.Class) == OL_MAIL_CLASS
    except Exception:
        return False


def _is_unread(item) -> bool:
    try:
        return bool(item.UnRead)
    except Exception:
        return False


def _has_category(item, category: str) -> bool:
    wanted = category.casefold()
    current = str(getattr(item, "Categories", "") or "")
    return any(part.strip().casefold() == wanted for part in current.split(",") if part.strip())


def _reject_unfiltered_inbox(namespace, folder, subject_contains: str) -> None:
    if subject_contains.strip():
        return
    try:
        inbox = namespace.GetDefaultFolder(OL_FOLDER_INBOX)
        same = folder.EntryID == inbox.EntryID
    except Exception:
        same = str(getattr(folder, "Name", "")).casefold() == "inbox"
    if same:
        raise MailError(
            "The selected folder is the Inbox. Set outlook.subject_contains, "
            "or point outlook.folder_path at a dedicated folder."
        )
