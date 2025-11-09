from src.emailer import send_email

def test_smtp_connection():
    """Test SMTP connection and email sending functionality."""
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