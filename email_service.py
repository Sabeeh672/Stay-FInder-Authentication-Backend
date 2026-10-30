import os
import requests

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

def send_otp_email(receiver_email: str, otp_code: str) -> bool:
    body = (
        "Hi,\n\n"
        "Thank you for signing up with StayFinder!\n"
        f"Your verification code is: {otp_code}\n"
        "This code expires in 10 minutes.\n\n"
        "Regards,\nStayFinder Team"
    )
    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": BREVO_API_KEY,
                "accept": "application/json",
                "content-type": "application/json",
            },
            json={
                "sender": {"name": "StayFinder", "email": SENDER_EMAIL},
                "to": [{"email": receiver_email}],
                "subject": "StayFinder - Your Email Verification Code",
                "textContent": body,
            },
            timeout=15,
        )
        if r.status_code in (200, 201):
            print(f"[EMAIL SUCCESS] OTP sent to {receiver_email}")
            return True
        print(f"[EMAIL ERROR] {r.status_code}: {r.text}")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False
