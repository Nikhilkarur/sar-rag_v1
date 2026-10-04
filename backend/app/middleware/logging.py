import time
from typing import Optional
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.api_log import APILog
from app.utils import request_context
from jose import jwt, JWTError
from app.config import settings

class APILoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else None
        # Expose the caller's IP to the rest of the request (AuditLog.actor_ip). Set
        # before call_next so the endpoint's task and threadpool workers inherit it.
        ip_token = request_context.client_ip.set(client_ip)
        try:
            if request.url.path in ["/health", "/docs", "/openapi.json"]:
                return await call_next(request)

            start_time = time.time()
            # An exception escaping call_next becomes a 500 at ServerErrorMiddleware
            # (outside us); record it as such instead of skipping the log row.
            status_code = 500
            try:
                response = await call_next(request)
                status_code = response.status_code
                return response
            finally:
                process_time_ms = int((time.time() - start_time) * 1000)
                try:
                    # Sync DB work: off the event loop, and the pooled connection is
                    # only held for the write itself, not for the whole request.
                    await run_in_threadpool(
                        _write_api_log,
                        auth_header=request.headers.get("Authorization"),
                        x_tenant_id=request.headers.get("X-Tenant-ID"),
                        method=request.method,
                        endpoint=request.url.path,
                        status_code=status_code,
                        request_ip=client_ip,
                        user_agent=request.headers.get("user-agent"),
                        latency_ms=process_time_ms,
                    )
                except Exception as e:
                    # Don't let logging failures break the API response (or mask the
                    # original exception on the error path)
                    print(f"Failed to write API log: {e}")
        finally:
            request_context.client_ip.reset(ip_token)


def _write_api_log(*, auth_header: Optional[str], x_tenant_id: Optional[str], method: str,
                   endpoint: str, status_code: int, request_ip: Optional[str],
                   user_agent: Optional[str], latency_ms: int) -> None:
    # Extract user_id and tenant_id
    user_id = None
    tenant_id = None

    # Try extract from JWT
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
        except JWTError:
            pass

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
            method=method,
            # Clip to the column widths: an over-long path/UA must not drop the row
            endpoint=endpoint[:255],
            status_code=status_code,
            request_ip=request_ip,
            user_agent=user_agent[:500] if user_agent else None,
            latency_ms=latency_ms
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        # Don't let logging failures break the API response
        print(f"Failed to write API log: {e}")
    finally:
        db.close()
