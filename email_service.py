import smtplib
import socket
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Render environment variables ya local defaults
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "sabeehshah672@gmail.com")
APP_PASSWORD = os.getenv("APP_PASSWORD", "mqjc vufj pnfn unyt")

def send_otp_email(receiver_email: str, otp_code: str):
    subject = "StayFinder - Your Email Verification Code"
    body = f"""
    Hi,
    
    Thank you for signing up with StayFinder! 
    Your verification code is: {otp_code}
    
    Please enter this code in the app to activate your account.
    
    Regards,
    StayFinder Team
    """

    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        # Render par IPv6 error se bachne ke liye direct IPv4 resolve karein
        host = "smtp.gmail.com"
        port = 587
        
        ip_address = socket.gethostbyname(host)
        
        server = smtplib.SMTP(ip_address, port)
        server.starttls(server_hostname=host)
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
        server.quit()
        
        print(f" [EMAIL SUCCESS] OTP sent to {receiver_email}")
        return True
    except Exception as e:
        print(f" [EMAIL ERROR] Failed to send email: {e}")
        return False
