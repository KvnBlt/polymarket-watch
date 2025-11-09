import os
from src.emailer import send_email

def test_smtp_connection():
    """Test SMTP connection and email sending functionality."""
    print("Starting email test...")
    print(f"SMTP_HOST: {os.environ.get('SMTP_HOST')}")
    print(f"SMTP_PORT: {os.environ.get('SMTP_PORT')}")
    print(f"SMTP_USER: {os.environ.get('SMTP_USER')}")
    print(f"SMTP_FROM: {os.environ.get('SMTP_FROM')}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    
    smtp_conf = {
        "timeout": 30,
        "use_starttls": True
    }
    
    try:
        print("Attempting to send email...")
        send_email(
            smtp_conf=smtp_conf,
            to_addr="sokhaar313@gmail.com",
            subject="Test Email Connection",
            body="This is a test email from your Polymarket Watch application. If you receive this, the SMTP configuration is working correctly!"
        )
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise

if __name__ == "__main__":
    test_smtp_connection()