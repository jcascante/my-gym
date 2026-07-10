from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import InvalidTokenError, decode_token
from app.core.database import get_db
from app.crud.user import get_user_by_id
from app.models import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        sub: str = payload.get("sub")
        if not sub:
            raise InvalidTokenError()
        user_id: int = int(sub)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token format")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
