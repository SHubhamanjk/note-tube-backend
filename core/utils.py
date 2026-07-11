import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
from core.config import settings

def get_ist_now() -> datetime:
    """Returns current datetime in Indian Standard Time (IST)."""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

async def send_email(recipient: str, subject: str, body: str, html_body: str = None) -> bool:
    """Send email using Gmail SMTP"""
    try:
        from_email = settings.SMTP_FROM_EMAIL
        from_name = settings.SMTP_FROM_NAME
        gmail_password = settings.GMAIL_APP_PASSWORD
        
        if gmail_password:
            gmail_password = gmail_password.replace(" ", "")
        
        if not from_email or not gmail_password:
            print("Missing SMTP credentials.")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = recipient
        
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, gmail_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

async def send_otp_email(recipient: str, otp: str, context: str = "login") -> bool:
    """Send OTP verification email for login or forgot password"""
    if context == "forgot_password":
        subject = "Password Reset OTP - Medha.ai"
        intro_text = "You requested to reset your password for your Medha.ai account."
        action_text = "If you didn't request this password reset, please ignore this email and your password will remain unchanged."
    else:
        subject = "Login OTP - Medha.ai"
        intro_text = "You requested to log in to your Medha.ai account."
        action_text = "If you didn't request this login, please ignore this email."

    body = f"""
Hello,

{intro_text}

Your OTP (One-Time Password) is: {otp}

This OTP will expire in 2 minutes.

{action_text}

Best regards,
Medha.ai Team
"""
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .otp-box {{ background: white; border: 2px dashed #667eea; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
        .otp-code {{ font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 8px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Medha.ai Security</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>{intro_text}</p>
            <p>Your One-Time Password (OTP) is:</p>
            <div class="otp-box">
                <div class="otp-code">{otp}</div>
            </div>
            <p><strong>This OTP will expire in 2 minutes.</strong></p>
            <p>{action_text}</p>
            <p>Best regards,<br>Medha.ai Team</p>
        </div>
        <div class="footer">
            <p>© 2026 Medha.ai. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    return await send_email(recipient, subject, body, html_body)
