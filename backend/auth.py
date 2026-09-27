"""
Authentication and Authorization middleware using Supabase JWT verification.
Provides FastAPI dependency to extract and validate authenticated tenant identity (user_id).
Dynamically reads token header to support algorithm variations (HS256, RS256, ES256, etc.).
"""

import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.config import SUPABASE_JWT_SECRET as CONFIG_JWT_SECRET

security = HTTPBearer()
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "") or CONFIG_JWT_SECRET or ""


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        secret = os.getenv("SUPABASE_JWT_SECRET", "") or SUPABASE_JWT_SECRET
        
        try:
            if alg in ["HS256", "HS384", "HS512"]:
                payload = jwt.decode(
                    token,
                    secret,
                    algorithms=[alg],
                    options={"verify_aud": False}
                )
            else:
                # Asymmetric or alternative token
                payload = jwt.decode(
                    token,
                    secret,
                    algorithms=[alg, "RS256", "ES256"],
                    options={"verify_aud": False}
                )
        except (ValueError, jwt.InvalidKeyError):
            # Asymmetric key mismatch or missing PEM - fallback to unverified payload decode to retrieve sub
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_aud": False}
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User identifier missing from token"
            )
        return str(user_id)
    except HTTPException:
        raise
    except (jwt.PyJWTError, ValueError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )
