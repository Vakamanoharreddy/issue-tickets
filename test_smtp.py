import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import traceback

def load_env_variables():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key, val = parts[0].strip(), parts[1].strip()
                        os.environ[key] = val.strip("\"'")

print("Loading configuration settings...")
load_env_variables()

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
try:
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
except ValueError:
    SMTP_PORT = 587

SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "your_email@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "your_app_password")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")

# Main emails
MAIN_EMAILS_STR = os.environ.get("MAIN_EMAILS", "admin@example.com,info@example.com")
MAIN_EMAILS = [email.strip() for email in MAIN_EMAILS_STR.split(",") if email.strip()]

print(f"SMTP Server:   {SMTP_SERVER}")
print(f"SMTP Port:     {SMTP_PORT}")
print(f"SMTP User:     {SMTP_USERNAME}")
print(f"Sender Email:  {SENDER_EMAIL}")
print(f"Recipients:    {', '.join(MAIN_EMAILS)}")

if SMTP_USERNAME == "your_email@gmail.com" or SMTP_PASSWORD == "your_app_password":
    print("\n[WARNING] You are using placeholder SMTP credentials.")
    print("Please copy '.env.example' to '.env' and fill in your real credentials first!")
    exit(1)

print("\nAttempting to connect to SMTP server...")
try:
    if SMTP_PORT == 465:
        print("Using SMTP_SSL (Port 465)...")
        server_conn = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
    else:
        print("Using SMTP (Port 587/other)...")
        server_conn = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        print("Sending STARTTLS...")
        server_conn.starttls()
    
    with server_conn as server:
        print("Logging in...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        print("Constructing test message...")
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(MAIN_EMAILS)
        msg['Subject'] = "BridgeThings Ticket System - SMTP Test Email"
        body = "This is a test email sent from the BridgeThings Ticket System SMTP verification script. Your email notifications are configured correctly!"
        msg.attach(MIMEText(body, 'plain'))
        
        print("Sending mail...")
        server.sendmail(SENDER_EMAIL, MAIN_EMAILS, msg.as_string())
        
    print("\n[SUCCESS] Test email successfully sent!")
except Exception as e:
    print("\n[ERROR] Failed to send email.")
    print(f"Exception Type: {type(e).__name__}")
    print(f"Error Details:  {e}")
    print("\nTraceback:")
    traceback.print_exc()
