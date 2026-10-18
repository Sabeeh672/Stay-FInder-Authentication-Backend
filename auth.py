import random
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from database import get_auth_connection

router = APIRouter()

# ------------------------------------------------------------------
# Validator Helper
# ------------------------------------------------------------------
def verify_email_domain(email_str: str) -> str:
    if not re.search(r"^[a-z0-9._%+-]+@(gmail|email)\.com$", email_str.lower()):
        raise ValueError("Gmail is incorrect, please check it again")
    return email_str

# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
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
    email: EmailStr
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return verify_email_domain(value)


# ------------------------------------------------------------------
# User Auth Endpoints
# ------------------------------------------------------------------
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

    print(f" [OTP DEBUG] VERIFICATION CODE FOR {user_data.email} IS: {generated_otp}")
    return {"message": "Signup successful! Please verify your account.", "otp_debug": generated_otp}


@router.post("/verify-otp/")
def verify_otp(data: VerifyOtpRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        if str(user["otp_code"]) != str(data.otp):
            raise HTTPException(status_code=400, detail="Invalid OTP code. Please check again.")

        cursor.execute(
            "UPDATE users SET is_active = %s, otp_code = %s WHERE email = %s",
            (True, None, data.email),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Verify OTP Error: {e}")
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
        print(f" Login Error: {e}")
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
    # ------------------------------------------------------------------
# Admin Endpoints (Added for testing & management)
# ------------------------------------------------------------------
class AdminActionRequest(BaseModel):
    email: EmailStr

@router.get("/admin/users/")
def get_all_users():
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT name, email, is_active FROM users") # id hata diya
        users = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        count = cursor.fetchone()["total"]
    except Exception as e:
        print(f" Admin Get Users Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()
    return {"total_users": count, "users": users}


@router.post("/admin/verify-user/")
def admin_verify_user(data: AdminActionRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="User not found")

        cursor.execute(
            "UPDATE users SET is_active = %s, otp_code = %s WHERE email = %s",
            (True, None, data.email),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Admin Verify Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()
    return {"message": f"User {data.email} successfully verified by admin!"}


@router.post("/admin/delete-user/")
def admin_delete_user(data: AdminActionRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="User not found")

        cursor.execute("DELETE FROM users WHERE email = %s", (data.email,))
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Admin Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()
    return {"message": f"User {data.email} deleted successfully by admin!"}
