import random
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from database import get_auth_connection
from email_service import send_otp_email

router = APIRouter()


# ------------------------------------------------------------------
# Validator Helper (Clean and lowercase email to prevent mismatch)
# ------------------------------------------------------------------
def verify_email_domain(email_str: str) -> str:
    cleaned_email = email_str.strip().lower()
    if not re.search(r"^[a-z0-9._%+-]+@(gmail|email)\.com$", cleaned_email):
        raise ValueError("Gmail is incorrect, please check it again")
    return cleaned_email


# ------------------------------------------------------------------
# Pydantic Models (Using str instead of EmailStr to avoid email-validator issues)
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
# User Auth Endpoints
# ------------------------------------------------------------------
@router.delete("/admin/delete-user/")
def delete_specific_user(email: str):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        # Sirf di gayi email wale user ko delete karega
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        connection.commit()

        if cursor.rowcount == 0:
            return {"message": f"No user found with email: {email}"}

        return {"message": f"User with email {email} deleted successfully! You can sign up again."}
    except Exception as e:
        print(f"Delete User Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()
@router.post("/signup/")
def signup(user_data: SignupRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        generated_otp = str(random.randint(100000, 999999))

        cursor.execute(
            "INSERT INTO users (name, email, password, otp_code, is_active) VALUES (%s, %s, %s, %s, %s)",
            (user_data.name, user_data.email, user_data.password, generated_otp, False),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Signup Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    # --- Yahan asli email bhejney ka function call hoga ---
    email_sent = send_otp_email(user_data.email, generated_otp)

    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please check backend logs.")

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

        db_otp = str(user["otp_code"]).strip() if user["otp_code"] else ""
        input_otp = str(data.otp).strip()

        if db_otp != input_otp:
            raise HTTPException(status_code=400, detail="Invalid OTP code. Please check again.")

        cursor.execute(
            "UPDATE users SET is_active = %s, otp_code = %s WHERE email = %s",
            (True, None, data.email),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Verify OTP Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    if not user["is_active"]:
        raise HTTPException(status_code=400, detail="Please verify your email first using /verify-otp/")
    if user["password"] != data.password:
        raise HTTPException(status_code=400, detail="Incorrect password")

    return {"message": "Login successful", "user": {"name": user["name"], "email": user["email"]}}
