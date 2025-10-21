from passlib.context import CryptContext
from passlib.exc import UnknownHashError

# Use Argon2 for modern, secure password hashing
pwd_cxt = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a plain text password using Argon2.
    """
    return pwd_cxt.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its hashed version.
    """
    try:
        return pwd_cxt.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False

