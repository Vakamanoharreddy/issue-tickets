import os

print("=== BridgeThings Ticket System SMTP Setup ===")
email = input("Enter your Gmail address (e.g. user@gmail.com): ").strip()
password = input("Enter your 16-character Gmail App Password (e.g. abcd efgh ijkl mnop): ").strip()

# Remove spaces from the app password if any
password = password.replace(" ", "")

if not email or not password:
    print("Error: Email and password cannot be empty.")
    exit(1)

env_content = f"""# SMTP Configuration for BridgeThings Ticket System
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME={email}
SMTP_PASSWORD={password}
SENDER_EMAIL={email}

# Comma-separated list of admin/monitoring emails to CC on all notifications
MAIN_EMAILS=admin@example.com,info@example.com
"""

with open(".env", "w") as f:
    f.write(env_content)

print("\n[SUCCESS] .env file updated successfully!")
print(f"SMTP Username set to: {email}")
print("App Password updated.")
print("\nNow you can run the test script to verify: python test_smtp.py")
