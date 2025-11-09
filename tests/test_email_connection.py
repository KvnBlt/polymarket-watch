import os
import sys

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.emailer import send_email

def test_smtp_connection():
    smtp_conf = {
        "timeout": 30,
        "use_starttls": True
    }
    
    try:
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