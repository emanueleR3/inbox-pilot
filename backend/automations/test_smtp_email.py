"""
Simple test script for SMTP email sending.
Fill in the parameters below and run the script.
"""

from chatbot.services.email_service import send_email

SENDER_PASSWORD = ""  # Use app password for Gmail

# ============================================
# FILL IN THESE PARAMETERS
# ============================================

# SMTP server settings
SMTP_HOST = "smtp.studenti.polito.it"  # e.g., "smtp.gmail.com", "smtp.office365.com"
SMTP_PORT = 465  # Usually 587 for STARTTLS, 465 for SSL

# Sender credentials
SENDER_EMAIL = "student2@example.com"

# Recipient
RECEIVER_EMAIL = "dev4@example.com"

# Email content
SUBJECT = "Test Email from SMTP"
BODY = "This is a test email sent via SMTP."
BODY_TYPE = "text"  # "text" or "html"

# Optional: CC and BCC recipients (set to None if not needed)
CC_RECIPIENTS = None  # e.g., ["cc1@example.com", "cc2@example.com"]
BCC_RECIPIENTS = None  # e.g., ["bcc@example.com"]

# Optional: Attachments (set to None if not needed)
ATTACHMENTS = None  # e.g., ["/path/to/file1.pdf", "/path/to/file2.txt"]

# ============================================
# RUN THE TEST
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("Testing SMTP Email Send")
    print("=" * 50)
    print(f"Host: {SMTP_HOST}:{SMTP_PORT}")
    print(f"From: {SENDER_EMAIL}")
    print(f"To: {RECEIVER_EMAIL}")
    print(f"Subject: {SUBJECT}")
    print("=" * 50)
    
    try:
        result = send_email(
            sender_address=SENDER_EMAIL,
            password=SENDER_PASSWORD,
            receiver_address=RECEIVER_EMAIL,
            subject=SUBJECT,
            body=BODY,
            provider="smtp",
            host=SMTP_HOST,
            port=SMTP_PORT,
            body_type=BODY_TYPE,
            cc_recipients=CC_RECIPIENTS,
            bcc_recipients=BCC_RECIPIENTS,
            attachments=ATTACHMENTS
        )
        print("\n✅ SUCCESS!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
