import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Yahan apni asal Gmail ID aur 16-digit app password likhein
SENDER_EMAIL = "sabeehshah672@gmail.com"
APP_PASSWORD = "mqjc vufj pnfn unyt"  # Yahan apna 16-digit password dalein (spaces ke sath ya bagair dono chalte hain)


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
        # Gmail SMTP Server connect karein (Port 587 with TLS)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
        server.quit()
        print(f" [EMAIL SUCCESS] OTP sent to {receiver_email}")
        return True
    except Exception as e:
        print(f" [EMAIL ERROR] Failed to send email: {e}")
        return False