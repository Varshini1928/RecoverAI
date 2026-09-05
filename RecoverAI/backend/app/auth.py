from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import get_settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()
_settings = get_settings()
_demo_hash = pwd.hash(_settings.admin_password)

def verify_login(username: str, password: str):
    return username == _settings.admin_username and pwd.verify(password, _demo_hash)
def create_token(subject: str):
    exp = datetime.now(timezone.utc) + timedelta(minutes=_settings.access_token_minutes)
    return jwt.encode({"sub": subject, "exp": exp}, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)
def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        data = jwt.decode(credentials.credentials, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm])
        if data.get("sub") != _settings.admin_username: raise ValueError
        return data["sub"]
    except (JWTError, ValueError):
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate":"Bearer"})

