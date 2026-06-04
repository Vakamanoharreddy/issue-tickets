import os

print("=== BridgeThings Ticket System SMTP Setup ===")
email = input("Enter your Gmail address (e.g. user@gmail.com): ").strip()
password = input("Enter your 16-character Gmail App Password (e.g. abcd efgh ijkl mnop): ").strip()

# Remove spaces from the app password if any
password = password.replace(" ", "")

if not email or not password:
    print("Error: Email and password cannot be empty.")
    exit(1)

print("\n--- PostgreSQL Database Configuration ---")
db_user = input("Enter DB Username (e.g. postgres): ").strip()
db_pass = input("Enter DB Password: ").strip()
db_host = input("Enter DB Host (e.g. localhost): ").strip() or "localhost"
db_port = input("Enter DB Port (e.g. 5432): ").strip() or "5432"
db_name = input("Enter Database Name: ").strip()

db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

env_content = f"""# SMTP Configuration for BridgeThings Ticket System
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME={email}
SMTP_PASSWORD={password}
SENDER_EMAIL={email}

# Database Configuration
DATABASE_URL={db_url}

# Comma-separated list of admin/monitoring emails to CC on all notifications
MAIN_EMAILS=admin@example.com,info@example.com
"""

with open(".env", "w") as f:
    f.write(env_content)

print("\n[SUCCESS] .env file updated successfully!")
print(f"SMTP Username set to: {email}")
print("App Password updated.")
print("\nNow you can run the test script to verify: python test_smtp.py")
