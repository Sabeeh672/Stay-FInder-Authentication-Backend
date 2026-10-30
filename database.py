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
        autocommit=True,
        ssl={"ca": os.environ["DB_SSL_CA"]} if os.getenv("DB_SSL_CA") else None,
    )

def setup_auth_database():
    try:
        conn = get_auth_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100) UNIQUE,
                    password VARCHAR(100),
                    otp_code VARCHAR(10) NULL,
                    otp_expires_at DATETIME NULL,
                    is_active BOOLEAN DEFAULT FALSE
                )
            """)
            # Purani table mein naya column add karna (agar pehle se hai to error ignore)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN otp_expires_at DATETIME NULL")
                print("[Auth DB]: Column otp_expires_at added.")
            except pymysql.err.OperationalError:
                pass  # column pehle se maujood hai
        conn.close()
        print("[Auth DB]: Users Table Initialized Successfully!")
    except Exception as e:
        print(f"[Auth DB Setup Error]: {e}")
def setup_hostel_tables():
    try:
        conn = get_auth_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hostels (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    address VARCHAR(255) NULL,
                    image_url VARCHAR(500) NULL,
                    rent_per_room INT NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hostel_reviews (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hostel_id INT NOT NULL,
                    user_email VARCHAR(100) NOT NULL,
                    rating TINYINT NOT NULL,
                    comment VARCHAR(500) NULL,
                    INDEX idx_hostel (hostel_id)
                )
            """)
        conn.close()
        print("[Hostel DB]: Tables Initialized Successfully!")
    except Exception as e:
        print(f"[Hostel DB Setup Error]: {e}")
