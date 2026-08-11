import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email(settings, to_email, subject, html_body, text_body=None):
    if not settings or not settings.email_enabled:
        logger.info("E-posta devre dışı — mesaj gönderilmedi: %s -> %s", subject, to_email)
        return False

    if not settings.smtp_host or not settings.smtp_from:
        logger.warning("SMTP ayarları eksik — e-posta gönderilemedi.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    plain = text_body or html_body.replace("<br>", "\n").replace("<p>", "").replace("</p>", "\n")
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port or 587, timeout=15) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logger.error("E-posta gönderilemedi: %s", exc)
        return False


def notify_appointment_created(settings, appointment, therapist, site_name, invite_url=None):
    date_str = appointment.appointment_date.strftime("%d.%m.%Y")
    time_str = appointment.appointment_time.strftime("%H:%M")
    session = appointment.SESSION_LABELS.get(appointment.session_type, appointment.session_type)

    invite_block = ""
    if invite_url:
        invite_block = f"""
        <p><strong>Danışan paneli:</strong> Randevularınızı ve sonuçlarınızı görmek için hesabınızı aktifleştirin:<br>
        <a href="{invite_url}">{invite_url}</a></p>
        """

    patient_html = f"""
    <h2>Randevunuz Alındı</h2>
    <p>Sayın {appointment.patient_name},</p>
    <p><strong>{site_name}</strong> üzerinden randevu talebiniz alınmıştır.</p>
    <ul>
      <li><strong>Terapist:</strong> {therapist.name}</li>
      <li><strong>Tarih:</strong> {date_str}</li>
      <li><strong>Saat:</strong> {time_str}</li>
      <li><strong>Tür:</strong> {session}</li>
      <li><strong>Durum:</strong> Onay bekleniyor</li>
    </ul>
    {invite_block}
    <p>Onaylandığında ayrıca bilgilendirileceksiniz.</p>
    """
    send_email(
        settings,
        appointment.patient_email,
        f"Randevu Talebi — {site_name}",
        patient_html,
    )

    if settings.admin_email:
        admin_html = f"""
        <h2>Yeni Randevu Talebi</h2>
        <ul>
          <li><strong>Danışan:</strong> {appointment.patient_name}</li>
          <li><strong>E-posta:</strong> {appointment.patient_email}</li>
          <li><strong>Telefon:</strong> {appointment.patient_phone}</li>
          <li><strong>Terapist:</strong> {therapist.name}</li>
          <li><strong>Tarih/Saat:</strong> {date_str} {time_str}</li>
        </ul>
        """
        send_email(settings, settings.admin_email, f"Yeni Randevu — {appointment.patient_name}", admin_html)


def notify_appointment_confirmed(settings, appointment, therapist, site_name):
    if appointment.status != "onaylandi":
        return

    date_str = appointment.appointment_date.strftime("%d.%m.%Y")
    time_str = appointment.appointment_time.strftime("%H:%M")

    patient_html = f"""
    <h2>Randevunuz Onaylandı</h2>
    <p>Sayın {appointment.patient_name},</p>
    <p>{therapist.name} ile <strong>{date_str} {time_str}</strong> randevunuz onaylanmıştır.</p>
    """
    send_email(settings, appointment.patient_email, f"Randevu Onayı — {site_name}", patient_html)

    if therapist.email:
        therapist_html = f"""
        <h2>Onaylanmış Randevu</h2>
        <ul>
          <li><strong>Danışan:</strong> {appointment.patient_name}</li>
          <li><strong>E-posta:</strong> {appointment.patient_email}</li>
          <li><strong>Telefon:</strong> {appointment.patient_phone}</li>
          <li><strong>Tarih/Saat:</strong> {date_str} {time_str}</li>
        </ul>
        """
        send_email(settings, therapist.email, f"Onaylanmış Randevu — {appointment.patient_name}", therapist_html)
