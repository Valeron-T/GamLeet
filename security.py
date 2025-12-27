import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

encryption_key = os.getenv("ENCRYPTION_KEY")
if not encryption_key:
    raise ValueError("ENCRYPTION_KEY not found in environment variables")

cipher = Fernet(encryption_key)

def encrypt_token(token: str) -> str:
    return cipher.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return cipher.decrypt(encrypted_token.encode()).decode()
