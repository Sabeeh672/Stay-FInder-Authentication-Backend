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
    # The database must already exist on Aiven.
    # This function creates the users table if it does not exist.
    conn = get_auth_connection()

    try:
        with conn.cursor() as cursor:
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

        conn.commit()
        print("[Auth DB]: Users Table Initialized!")

    finally:
        conn.close()
