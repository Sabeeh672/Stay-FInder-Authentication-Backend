import re
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from database import get_auth_connection
from email_service import send_otp_email

router = APIRouter()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def verify_email_domain(email_str: str) -> str:
    cleaned_email = email_str.strip().lower()
    if not re.search(r"^[a-z0-9._%+-]+@(gmail|email)\.com$", cleaned_email):
        raise ValueError("Gmail is incorrect, please check it again")
    return cleaned_email


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def new_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)


# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z\s]+$", value.strip()):
            raise ValueError("Name can only contain letters and spaces.")
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return verify_email_domain(value)


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return verify_email_domain(value)

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return verify_email_domain(value)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.post("/signup/")
def signup(user_data: SignupRequest):
    otp = new_otp()
    expires = datetime.utcnow() + timedelta(minutes=10)
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (user_data.email,))
        existing = cursor.fetchone()

        if existing:
            if existing["is_active"]:
                raise HTTPException(status_code=400, detail="Email already registered. Please login.")
            cursor.execute(
                "UPDATE users SET name=%s, password=%s, otp_code=%s, otp_expires_at=%s WHERE email=%s",
                (user_data.name, hash_password(user_data.password), otp, expires, user_data.email),
            )
        else:
            cursor.execute(
                "INSERT INTO users (name, email, password, otp_code, otp_expires_at, is_active) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_data.name, user_data.email, hash_password(user_data.password), otp, expires, False),
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup Error: {e}")
        raise HTTPException(status_code=500, detail="Server error. Please try again.")
    finally:
        connection.close()

    if not send_otp_email(user_data.email, otp):
        raise HTTPException(status_code=500, detail="Failed to send verification email. Try again.")

    return {"message": "Signup successful! Please check your email for the OTP."}


@router.post("/verify-otp/")
def verify_otp(data: VerifyOtpRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        if not user["otp_code"]:
            raise HTTPException(status_code=400, detail="No OTP pending. Please sign up again.")
        if user["otp_expires_at"] and datetime.utcnow() > user["otp_expires_at"]:
            raise HTTPException(status_code=400, detail="OTP expired. Please sign up again.")
        if user["otp_code"].strip() != data.otp.strip():
            raise HTTPException(status_code=400, detail="Invalid OTP code. Please check again.")

        cursor.execute(
            "UPDATE users SET is_active=%s, otp_code=NULL, otp_expires_at=NULL WHERE email=%s",
            (True, data.email),
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Verify OTP Error: {e}")
        raise HTTPException(status_code=500, detail="Server error. Please try again.")
    finally:
        connection.close()

    return {"message": "Account activated successfully! You can now log in."}


@router.post("/login/")
def login(data: LoginRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
        user = cursor.fetchone()
    except Exception as e:
        print(f"Login Error: {e}")
        raise HTTPException(status_code=500, detail="Server error. Please try again.")
    finally:
        connection.close()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    if not user["is_active"]:
        raise HTTPException(status_code=400, detail="Please verify your email first.")

    try:
        ok = bcrypt.checkpw(data.password.encode(), user["password"].encode())
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=400, detail="Incorrect password")

    return {"message": "Login successful", "user": {"name": user["name"], "email": user["email"]}}
