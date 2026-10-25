"""Bearer-token authentication; disabled only when explicitly configured for local development."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


security_scheme = HTTPBearer(auto_error=False)



def _secret_key() -> str:
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
                raise RuntimeError("Set JWT_SECRET_KEY to issue or verify access tokens")
        return secret



def create_access_token(subject: str, *, role: str = "analyst", expires_minutes: int = 60) -> str:
        from jose import jwt

        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        payload = {"sub": subject, "role": role, "exp": expire}
        return jwt.encode(payload, _secret_key(), algorithm="HS256")



def decode_access_token(token: str) -> dict[str, Any]:
        from jose import JWTError, jwt


        try:
                return jwt.decode(token, _secret_key(), algorithms=["HS256"])
        except JWTError as exc:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from
exc



def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme)) -> dict[str, Any]:
        """Return the authenticated user's claims; disabled only via AUTH_DISABLED=true for local dev."""
        if os.getenv("AUTH_DISABLED", "false").lower() == "true":
                return {"sub": "local-dev-user", "role": "analyst"}
        if credentials is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        return decode_access_token(credentials.credentials)



def require_role(*allowed_roles: str):
        def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
                if user.get("role") not in allowed_roles:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
                return user


        return dependency
