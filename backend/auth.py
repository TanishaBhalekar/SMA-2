"""
Authentication and Authorization middleware using Supabase JWT verification.
Provides FastAPI dependency to extract and validate authenticated tenant identity (user_id).
"""

import os
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.config import SUPABASE_JWT_SECRET

security = HTTPBearer(auto_error=True)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency that validates Supabase JWT from the Authorization Bearer header.
    Decodes the token using HS256 algorithm and verifies audience 'authenticated'.
    Returns the 'sub' claim representing the Supabase UUID of the authenticated user.
    """
    token = credentials.credentials
    secret = SUPABASE_JWT_SECRET or os.getenv("SUPABASE_JWT_SECRET")

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured on the server."
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: 'sub' claim is missing.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return str(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience. Expected 'authenticated'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
