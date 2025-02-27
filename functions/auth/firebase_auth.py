from fastapi import HTTPException, Header
from typing import Optional
import firebase_admin
from firebase_admin import auth

def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Verifica se o header 'Authorization' contém:
    'Bearer <Firebase_JWT_Token>'
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = parts[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token  # Retorna claims do usuário
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
