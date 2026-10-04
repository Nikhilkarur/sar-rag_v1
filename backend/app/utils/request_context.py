"""
Per-request context for code that has no access to the Request object.

Set by APILoggingMiddleware for every HTTP request. Context variables are copied into
the endpoint's task and into threadpool workers (sync endpoints / dependencies), so a
sync handler deep in a service sees the values of the request it is serving. Outside a
request (scripts, startup hooks) they hold their defaults.
"""
from contextvars import ContextVar
from typing import Optional

# Caller's IP (request.client.host). Read by the AuditLog before_insert listener so
# audit rows get actor_ip without every call site passing the request through.
client_ip: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
