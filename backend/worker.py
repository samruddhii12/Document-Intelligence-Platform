"""Run separately with python -m backend.worker; PostgreSQL owns durable state."""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, and_
from backend.database import SessionLocal
from backend.config import settings
from backend.models.db_models import Job, MailOutbox
from backend.services.jobs import enqueue_claim, process

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger=logging.getLogger(__name__)

def heartbeat(stop,job_id,token):
    while not stop.wait(30):
        try:
            with SessionLocal() as db:
                db.query(Job).filter_by(id=job_id,lease_token=token,status="processing").update({"lease_until":datetime.now(timezone.utc)+timedelta(seconds=settings.JOB_LEASE_SECONDS)})
                db.commit()
        except Exception: logger.exception("Could not renew job lease")

def send_mail():
    if not settings.SMTP_HOST or not settings.SMTP_FROM: return
    import smtplib
    from email.message import EmailMessage
    with SessionLocal() as db:
        now=datetime.now(timezone.utc)
        row=db.query(MailOutbox).filter(or_(MailOutbox.status=="queued",and_(MailOutbox.status=="sending",MailOutbox.lease_until<now)))\
            .order_by(MailOutbox.created_at).with_for_update(skip_locked=True).first()
        if not row: return
        row.status="sending"; row.attempts+=1; row.lease_until=now+timedelta(minutes=2)
        mail_id,recipient,subject,body=row.id,row.recipient,row.subject,row.body
        db.commit()
    message=EmailMessage(); message["From"]=settings.SMTP_FROM; message["To"]=recipient
    message["Subject"]=subject; message.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST,settings.SMTP_PORT,timeout=20) as smtp:
            smtp.ehlo()
            if settings.SMTP_STARTTLS:
                import ssl
                smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
            if settings.SMTP_USERNAME: smtp.login(settings.SMTP_USERNAME,settings.SMTP_PASSWORD)
            smtp.send_message(message)
        with SessionLocal() as db:
            row=db.get(MailOutbox,mail_id); row.status="sent"; row.body=""; db.commit()
    except Exception:
        logger.exception("Verification email delivery failed")
        with SessionLocal() as db:
            row=db.get(MailOutbox,mail_id); row.status="queued" if row.attempts<3 else "failed"; db.commit()

def main():
    logger.info("Document and data worker ready")
    last_cleanup=0
    while True:
        try:
            if time.monotonic()-last_cleanup>60:
                from backend.services.maintenance import cleanup
                with SessionLocal() as db: cleanup(db)
                last_cleanup=time.monotonic()
            send_mail()
            with SessionLocal() as db:
                claim=enqueue_claim(db)
            if not claim: time.sleep(2); continue
            stop=threading.Event(); thread=threading.Thread(target=heartbeat,args=(stop,*claim),daemon=True); thread.start()
            try:
                with SessionLocal() as db: process(db,*claim)
            finally: stop.set(); thread.join(timeout=2)
        except Exception:
            logger.exception("Worker loop failed; retrying"); time.sleep(5)

if __name__=="__main__": main()
