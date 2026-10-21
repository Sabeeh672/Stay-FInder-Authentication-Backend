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
# ------------------------------------------------------------------
# Hostel Owner Management (Admin Approval & ID Card Limit Flow)
# ------------------------------------------------------------------
class OwnerSignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    hostel_name: str
    id_card_number: str

    @field_validator("name", "hostel_name")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z\s]+$", value.strip()):
            raise ValueError("Field can only contain letters and spaces.")
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return verify_email_domain(value)


class OwnerLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return verify_email_domain(value)


class AdminOwnerEmailRequest(BaseModel):
    email: EmailStr


class UpdateOwnerLimitRequest(BaseModel):
    email: EmailStr
    new_limit: int


class RegisterHostelRequest(BaseModel):
    owner_email: EmailStr
    hostel_name: str
    location: str


@router.post("/owner/signup/")
def owner_signup(owner_data: OwnerSignupRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        # Check if email already exists
        cursor.execute("SELECT * FROM hostel_owners WHERE email = %s", (owner_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Owner email already registered")

        # Insert owner with is_approved = False and default hostel_limit = 1
        cursor.execute(
            "INSERT INTO hostel_owners (name, email, password, hostel_name, id_card_number, is_approved, hostel_limit) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (owner_data.name, owner_data.email, owner_data.password, owner_data.hostel_name, owner_data.id_card_number, False, 1),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Owner Signup Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    return {"message": "Account created successfully! Please wait for admin to approve your account."}


@router.post("/owner/login/")
def owner_login(data: OwnerLoginRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM hostel_owners WHERE email = %s", (data.email,))
        owner = cursor.fetchone()
    except Exception as e:
        print(f" Owner Login Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    if not owner:
        raise HTTPException(status_code=400, detail="Owner not found")
    
    # Check if admin approved the owner
    if not owner["is_approved"]:
        raise HTTPException(status_code=403, detail="Wait for admin to approve you. Your account is pending approval.")
    
    if owner["password"] != data.password:
        raise HTTPException(status_code=400, detail="Incorrect password")

    return {"message": "Owner login successful", "owner": {"name": owner["name"], "email": owner["email"], "hostel_name": owner["hostel_name"]}}


# ------------------------------------------------------------------
# Admin Endpoints for Hostel Owners
# ------------------------------------------------------------------
@router.get("/admin/owners/")
def get_all_owners():
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, name, email, hostel_name, id_card_number, is_approved, hostel_limit FROM hostel_owners")
        owners = cursor.fetchall()
    except Exception as e:
        print(f" Admin Get Owners Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()
    return {"owners": owners}


@router.post("/admin/approve-owner/")
def admin_approve_owner(data: AdminOwnerEmailRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM hostel_owners WHERE email = %s", (data.email,))
        owner = cursor.fetchone()

        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")

        cursor.execute(
            "UPDATE hostel_owners SET is_approved = %s WHERE email = %s",
            (True, data.email),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Admin Approve Owner Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    return {"message": f"Owner {data.email} has been approved successfully!"}


@router.post("/admin/update-owner-limit/")
def admin_update_owner_limit(data: UpdateOwnerLimitRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM hostel_owners WHERE email = %s", (data.email,))
        owner = cursor.fetchone()

        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")

        cursor.execute(
            "UPDATE hostel_owners SET hostel_limit = %s WHERE email = %s",
            (data.new_limit, data.email),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Admin Update Limit Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    return {"message": f"Hostel limit for {data.email} increased to {data.new_limit} successfully!"}


# ------------------------------------------------------------------
# Hostel Registration with ID Card Limit Validation
# ------------------------------------------------------------------
@router.post("/owner/register-hostel/")
def register_hostel(data: RegisterHostelRequest):
    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        # Get owner details including id_card_number and hostel_limit
        cursor.execute("SELECT * FROM hostel_owners WHERE email = %s", (data.owner_email,))
        owner = cursor.fetchone()

        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        if not owner["is_approved"]:
            raise HTTPException(status_code=403, detail="Your account is not approved by admin yet.")

        id_card = owner["id_card_number"]
        allowed_limit = owner["hostel_limit"]

        # Count how many hostels are already registered by this ID card (or owner email)
        cursor.execute("SELECT COUNT(*) as total FROM registered_hostels WHERE id_card_number = %s", (id_card,))
        result = cursor.fetchone()
        current_registered_count = result["total"] if result else 0

        if current_registered_count >= allowed_limit:
            raise HTTPException(
                status_code=400, 
                detail=f"Hostel limit reached ({current_registered_count}/{allowed_limit}). Contact admin to increase your hostel limit."
            )

        # Register the new hostel
        cursor.execute(
            "INSERT INTO registered_hostels (owner_email, id_card_number, hostel_name, location) VALUES (%s, %s, %s, %s)",
            (data.owner_email, id_card, data.hostel_name, data.location),
        )
        connection.commit()
    except HTTPException:
        raise
    except Exception as e:
        print(f" Register Hostel Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    return {"message": f"Hostel '{data.hostel_name}' registered successfully!"}
