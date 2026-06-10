import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.api_log import APILog
from jose import jwt, JWTError
from app.config import settings

class APILoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time_ms = int((time.time() - start_time) * 1000)
        
        # Extract user_id and tenant_id
        user_id = None
        tenant_id = None
        
        # Try extract from JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = payload.get("sub")
            except JWTError:
                pass
                
        # Try extract from Headers for API calls
        x_tenant_id = request.headers.get("X-Tenant-ID")
        
        db: Session = SessionLocal()
        try:
            # If we have user_id, get tenant_id from user
            if user_id:
                from app.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    tenant_id = user.tenant_id
                else:
                    # Token signed for a since-deleted user: keep the log row
                    # (FK would reject the orphan id and drop the audit entry)
                    user_id = None
            # If we have X-Tenant-ID, get tenant_id from public id
            elif x_tenant_id:
                from app.models.tenant import Tenant
                tenant = db.query(Tenant).filter(Tenant.tenant_id_public == x_tenant_id).first()
                if tenant:
                    tenant_id = tenant.id

            log_entry = APILog(
                tenant_id=tenant_id,
                user_id=user_id,
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                request_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                latency_ms=process_time_ms
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            # Don't let logging failures break the API response
            print(f"Failed to write API log: {e}")
        finally:
            db.close()
            
        return response
