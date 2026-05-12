"""PST file parser — tries pypff first, falls back to win32com (Outlook)."""

import email
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ParsedEmail:
    id: str
    subject: str
    sender: str
    recipients: list[str]
    date: Optional[datetime]
    body: str
    body_html: str
    folder: str


def _clean_body(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()[:8000]  # cap body length sent to Claude


def _strip_html(html: str) -> str:
    """Very light HTML → plain text."""
    if not html:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return _clean_body(text)


def parse_pst(file_path: str) -> list[ParsedEmail]:
    """Parse a PST file and return a flat list of emails."""
    try:
        return _parse_with_pypff(file_path)
    except ImportError:
        pass
    try:
        return _parse_with_win32com(file_path)
    except Exception:
        pass
    raise RuntimeError(
        "Cannot parse PST: install pypff or have Microsoft Outlook installed. "
        "Run: pip install pypff"
    )


def _parse_with_pypff(file_path: str) -> list[ParsedEmail]:
    import pypff  # type: ignore

    pst = pypff.file()
    pst.open(file_path)
    root = pst.get_root_folder()
    emails: list[ParsedEmail] = []
    _walk_pypff_folder(root, "", emails)
    pst.close()
    return emails


def _walk_pypff_folder(folder, path: str, emails: list[ParsedEmail]) -> None:
    import pypff  # type: ignore

    folder_name = folder.name or "Unknown"
    current_path = f"{path}/{folder_name}".lstrip("/")

    for i in range(folder.number_of_sub_messages):
        try:
            msg = folder.get_sub_message(i)
            emails.append(_pypff_message_to_email(msg, current_path, f"msg-{len(emails)}"))
        except Exception:
            continue

    for i in range(folder.number_of_sub_folders):
        try:
            sub = folder.get_sub_folder(i)
            _walk_pypff_folder(sub, current_path, emails)
        except Exception:
            continue


def _pypff_message_to_email(msg, folder: str, fallback_id: str) -> ParsedEmail:
    subject = getattr(msg, 'subject', '') or ''
    sender = getattr(msg, 'sender_name', '') or ''
    sender_email = getattr(msg, 'sender_email_address', '') or ''
    if sender_email and sender_email not in sender:
        sender = f"{sender} <{sender_email}>" if sender else sender_email

    plain = getattr(msg, 'plain_text_body', b'') or b''
    html = getattr(msg, 'html_body', b'') or b''

    try:
        plain_str = plain.decode('utf-8', errors='replace') if isinstance(plain, bytes) else plain
    except Exception:
        plain_str = ''
    try:
        html_str = html.decode('utf-8', errors='replace') if isinstance(html, bytes) else html
    except Exception:
        html_str = ''

    body = plain_str or _strip_html(html_str)

    date = None
    try:
        dt = msg.get_delivery_time()
        if dt:
            date = dt
    except Exception:
        pass

    return ParsedEmail(
        id=fallback_id,
        subject=subject,
        sender=sender,
        recipients=[],
        date=date,
        body=_clean_body(body),
        body_html=html_str[:2000],
        folder=folder,
    )


def _parse_with_win32com(file_path: str) -> list[ParsedEmail]:
    import win32com.client  # type: ignore
    import pythoncom  # type: ignore

    pythoncom.CoInitialize()
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    pst_store = outlook.AddStore(file_path)

    emails: list[ParsedEmail] = []
    root = pst_store.Folders.Item(1)
    _walk_com_folder(root, "", emails)

    outlook.RemoveStore(pst_store)
    pythoncom.CoUninitialize()
    return emails


def _walk_com_folder(folder, path: str, emails: list[ParsedEmail]) -> None:
    current_path = f"{path}/{folder.Name}".lstrip("/")
    try:
        items = folder.Items
        for item in items:
            try:
                if item.Class == 43:  # olMail
                    emails.append(_com_item_to_email(item, current_path, f"com-{len(emails)}"))
            except Exception:
                continue
    except Exception:
        pass

    try:
        for sub in folder.Folders:
            _walk_com_folder(sub, current_path, emails)
    except Exception:
        pass


def _com_item_to_email(item, folder: str, fallback_id: str) -> ParsedEmail:
    subject = getattr(item, 'Subject', '') or ''
    sender = getattr(item, 'SenderName', '') or ''
    sender_email = getattr(item, 'SenderEmailAddress', '') or ''
    if sender_email and '@' in sender_email and sender_email not in sender:
        sender = f"{sender} <{sender_email}>" if sender else sender_email

    body = _clean_body(getattr(item, 'Body', '') or '')
    body_html = (getattr(item, 'HTMLBody', '') or '')[:2000]

    date = None
    try:
        raw = getattr(item, 'ReceivedTime', None)
        if raw:
            date = raw
    except Exception:
        pass

    return ParsedEmail(
        id=fallback_id,
        subject=subject,
        sender=sender,
        recipients=[],
        date=date,
        body=body,
        body_html=body_html,
        folder=folder,
    )
