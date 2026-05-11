from datetime import datetime, timedelta
from jose import JWTError, jwt
import hashlib

SECRET_KEY = "cereviva-secret-key-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

PHOEBE_USERNAME = "phoebe"
PHOEBE_PASSWORD = "cereviva2026"

def verify_password(plain_password, stored_password):
    return plain_password == stored_password

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username != PHOEBE_USERNAME:
            return False
        return True
    except JWTError:
        return False