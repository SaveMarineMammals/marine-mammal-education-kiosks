"""MMEK admin alert Lambda: SES email + Sent.dm SMS on permanent host failures."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_ses = None


def _ses_client():
    global _ses
    if _ses is None:
        import boto3

        _ses = boto3.client("ses")
    return _ses


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise RuntimeError(f"missing required env {name}")
    return value


def _optional_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    if isinstance(body, str):
        body = body.strip() or "{}"
        return json.loads(body)
    if isinstance(body, dict):
        return body
    raise ValueError("unsupported body type")


def _bearer_ok(event: dict[str, Any], expected: str) -> bool:
    headers = event.get("headers") or {}
    # Function URL may lowercase header names
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return False
    token = auth[7:].strip()
    return bool(token) and token == expected


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


def _send_email(*, subject: str, body: str) -> None:
    from_addr = _env("SES_FROM_EMAIL")
    to_raw = _env("ALERT_EMAIL_TO")
    to_addrs = [a.strip() for a in to_raw.split(",") if a.strip()]
    if not to_addrs:
        raise RuntimeError("ALERT_EMAIL_TO is empty")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    _ses_client().send_raw_email(
        Source=from_addr,
        Destinations=to_addrs,
        RawMessage={"Data": msg.as_string()},
    )


def _send_sms(*, host: str, role: str, code: str, detail: str) -> None:
    api_key = _env("SENT_API_KEY")
    template_id = _optional_env("SENT_TEMPLATE_ID")
    template_name = _optional_env("SENT_TEMPLATE_NAME")
    if not template_id and not template_name:
        raise RuntimeError("set SENT_TEMPLATE_ID or SENT_TEMPLATE_NAME")

    to_raw = _env("ALERT_SMS_TO")
    recipients = [p.strip() for p in to_raw.split(",") if p.strip()]
    if not recipients:
        raise RuntimeError("ALERT_SMS_TO is empty")

    template: dict[str, Any] = {
        "parameters": {
            "host": host,
            "role": role,
            "code": code,
            "detail": detail[:200],
        }
    }
    if template_id:
        template["id"] = template_id
    if template_name:
        template["name"] = template_name

    payload = {
        "to": recipients,
        "channel": ["sms"],
        "template": template,
    }
    req = urllib.request.Request(
        "https://api.sent.dm/v3/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            logger.info("sent.dm status=%s body=%s", resp.status, raw[:500])
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"sent.dm HTTP {exc.code}: {err_body[:500]}") from exc


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        expected = _env("ALERT_INGEST_TOKEN")
    except RuntimeError as exc:
        logger.exception("misconfigured lambda")
        return _response(500, {"ok": False, "error": str(exc)})

    if not _bearer_ok(event, expected):
        return _response(401, {"ok": False, "error": "unauthorized"})

    try:
        data = _parse_body(event)
    except (json.JSONDecodeError, ValueError) as exc:
        return _response(400, {"ok": False, "error": f"invalid json: {exc}"})

    host = str(data.get("host") or "").strip() or "unknown"
    role = str(data.get("role") or "").strip() or "unknown"
    code = str(data.get("code") or "").strip() or "unknown"
    detail = str(data.get("detail") or "").strip() or "(no detail)"
    ts = str(data.get("ts") or "").strip() or "unknown"

    subject = f"[MMEK] {role} {host}: {code}"
    body = "\n".join(
        [
            "MMEK permanent failure alert",
            "",
            f"host: {host}",
            f"role: {role}",
            f"code: {code}",
            f"detail: {detail}",
            f"ts: {ts}",
            "",
            "See ops/runbooks/security-patching.md",
        ]
    )

    results: dict[str, str] = {}
    errors: list[str] = []

    try:
        _send_email(subject=subject, body=body)
        results["email"] = "ok"
    except Exception as exc:  # noqa: BLE001 — report channel failure, continue
        logger.exception("email failed")
        results["email"] = "error"
        errors.append(f"email: {exc}")

    try:
        _send_sms(host=host, role=role, code=code, detail=detail)
        results["sms"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.exception("sms failed")
        results["sms"] = "error"
        errors.append(f"sms: {exc}")

    if errors and results.get("email") != "ok" and results.get("sms") != "ok":
        return _response(502, {"ok": False, "channels": results, "errors": errors})

    status = 200 if not errors else 207
    return _response(status, {"ok": not errors, "channels": results, "errors": errors})
