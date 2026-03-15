"""Email notification system for new building work orders."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings
from src.database import BuildingOrder

logger = logging.getLogger(__name__)

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333; }}
  .header {{ background: #002664; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
  .header h1 {{ margin: 0; font-size: 20px; }}
  .content {{ padding: 20px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; }}
  .order-card {{ background: #f8f9fa; border-left: 4px solid #d63939; padding: 16px; margin: 12px 0; border-radius: 0 6px 6px 0; }}
  .order-card h3 {{ margin: 0 0 8px 0; color: #002664; }}
  .field {{ margin: 4px 0; }}
  .label {{ font-weight: 600; color: #555; }}
  .footer {{ margin-top: 20px; padding-top: 16px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #888; }}
  a {{ color: #2055d4; }}
</style>
</head>
<body>
<div class="header">
  <h1>NSW Building Commission &mdash; New Stop Work Orders Detected</h1>
</div>
<div class="content">
  <p>{count} new stop work order(s) found on the
  <a href="{register_url}">Register of Building Work Orders</a>.</p>

  {order_cards}

  <div class="footer">
    <p>This is an automated notification from the Building Orders Monitor.</p>
  </div>
</div>
</body>
</html>
"""

_CARD_TEMPLATE = """\
<div class="order-card">
  <h3>{title}</h3>
  <div class="field"><span class="label">Company:</span> {company}</div>
  <div class="field"><span class="label">ACN:</span> {acn}</div>
  <div class="field"><span class="label">Address:</span> {address}</div>
  <div class="field"><span class="label">Date:</span> {date}</div>
  <div class="field"><a href="{url}">View order details &rarr;</a></div>
</div>
"""


def send_notification(new_orders: list[BuildingOrder]) -> bool:
    """
    Send an HTML email listing newly discovered stop work orders.
    Returns True on success, False on failure.
    """
    if not new_orders:
        logger.info("No new orders — skipping notification.")
        return True

    if not settings.smtp_username or not settings.email_to:
        logger.warning(
            "Email not configured (SMTP_USERNAME / EMAIL_TO missing). "
            "Skipping notification."
        )
        return False

    cards = "\n".join(
        _CARD_TEMPLATE.format(
            title=o.title or "Unknown",
            company=o.company_name or "N/A",
            acn=o.acn or "N/A",
            address=o.address or "N/A",
            date=o.publication_date or o.first_seen.strftime("%Y-%m-%d"),
            url=o.source_url,
        )
        for o in new_orders
    )

    html_body = _HTML_TEMPLATE.format(
        count=len(new_orders),
        register_url=settings.base_url,
        order_cards=cards,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"[Building Orders Monitor] {len(new_orders)} new stop work order(s)"
    )
    msg["From"] = settings.email_from
    msg["To"] = settings.email_to

    # Plain-text fallback
    plain = "\n".join(
        f"- {o.company_name or o.title} | ACN: {o.acn or 'N/A'} | {o.source_url}"
        for o in new_orders
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.smtp_port == 465:
            # Implicit SSL
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.email_from, [settings.email_to], msg.as_string())
        else:
            # STARTTLS (port 587, etc.)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.email_from, [settings.email_to], msg.as_string())
        logger.info("Notification email sent to %s", settings.email_to)
        return True
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False
