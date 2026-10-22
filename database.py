import os
import pymysql

# Local development defaults; Render uses environment variables.
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "auth_database")
DB_PORT = int(os.getenv("DB_PORT", "3306"))


def get_auth_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        ssl={"ca": os.environ["DB_SSL_CA"]}
        if os.getenv("DB_SSL_CA")
        else None,
    )

def setup_auth_database():
    conn = get_auth_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100) UNIQUE,
                    password VARCHAR(100),
                    otp_code VARCHAR(6) NULL,
                    is_active BOOLEAN DEFAULT FALSE
                )
            """)
            # 2. Hostel Owners Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hostel_owners (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    hostel_name VARCHAR(255) NOT NULL,
                    id_card_number VARCHAR(50) NOT NULL,
                    is_approved BOOLEAN DEFAULT FALSE,
                    hostel_limit INT DEFAULT 1
                )
            """)
            # 3. Registered Hostels Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registered_hostels (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    owner_email VARCHAR(255) NOT NULL,
                    id_card_number VARCHAR(50) NOT NULL,
                    hostel_name VARCHAR(255) NOT NULL,
                    location VARCHAR(255) NOT NULL
                )
            """)
        conn.commit()
        print("[Auth DB]: All Tables Initialized Successfully!")
    finally:
        conn.close()
