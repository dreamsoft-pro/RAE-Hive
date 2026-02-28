import asyncio
import os
import smtplib
import structlog
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from base_agent.connector import HiveMindConnector

logger = structlog.get_logger("ReportingAgent")

# Load environment variables
load_dotenv()

# SMTP Configuration (from environment)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("REPORT_EMAIL_USER")
SMTP_PASS = os.getenv("REPORT_EMAIL_PASS")
RECIPIENT = os.getenv("REPORT_EMAIL_RECIPIENT")

async def generate_report(connector: HiveMindConnector):
    """Aggregates data from RAE and generates a human-readable report."""
    logger.info("generating_report_started")
    
    # 1. Calculate time window (last 2 hours)
    since_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    
    # 2. Fetch recent events using direct listing (Postgres fallback) to ensure fresh data
    # We query episodic and reflective layers
    params = {
        "project": "RAE-Hive",
        "since": since_time,
        "limit": 100
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{connector.base_url}/v2/memories/", headers=connector.headers, params=params)
        if resp.status_code != 200:
            logger.error("failed_to_fetch_events", status=resp.status_code)
            return "Error: Could not retrieve recent activity from RAE-Core."
        events = resp.json().get("results", [])
    
    if not events:
        return f"No significant activity recorded between {since_time} and now."

    # 3. Format context for LLM analysis (Filtering out management reports)
    context = ""
    for e in events:
        if "management_report" in e.get("tags", []):
            continue
        time = e.get("timestamp", "unknown")
        content = e.get("content", "")
        tags = ", ".join(e.get("tags", []))
        context += f"[{time}] [{tags}] {content}\n"

    if not context.strip():
        return "Only background maintenance detected. No new task progress."

    # 3. LLM Synthesis
    prompt = f"""
    You are the RAE Hive Chief Auditor (L3). Based on the following raw activity logs from the last 2 hours, 
    write a concise, high-level management report for the Owner.
    
    RAW LOGS:
    {context}
    
    REPORT STRUCTURE:
    1. Overall Status (Green/Yellow/Red)
    2. Accomplishments (What code was written/fixed)
    3. Incidents & Self-Healing (What loops were detected and how they were solved)
    4. Next Steps
    
    Write the report in Polish. Be direct and technical.
    """
    
    report_content = await connector.think(prompt)
    return report_content

def send_email(subject, body):
    """Sends the report via Gmail SMTP."""
    if not all([SMTP_USER, SMTP_PASS, RECIPIENT]):
        logger.error("email_config_missing", user=bool(SMTP_USER), recipient=bool(RECIPIENT))
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = RECIPIENT
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        logger.info("email_sent_successfully", recipient=RECIPIENT)
        return True
    except Exception as e:
        logger.error("email_failed", error=str(e))
        return False

async def reporting_loop():
    connector = HiveMindConnector(agent_role="reporter")
    logger.info("reporter_started", status="online")
    
    while True:
        try:
            report = await generate_report(connector)
            subject = f"RAE Hive Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Send Email
            send_email(subject, report)
            
            # Also store report in Reflective memory for history
            await connector.add_memory(
                content=report,
                layer="reflective",
                tags=["management_report", "snapshot"],
                metadata={"type": "periodic_report"}
            )
            
        except Exception as e:
            logger.error("reporter_loop_error", error=str(e))
            
        # Wait for 2 hours
        await asyncio.sleep(7200)

if __name__ == "__main__":
    asyncio.run(reporting_loop())
