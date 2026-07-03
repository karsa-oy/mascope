from fastapi_users.authentication import CookieTransport

from mascope_backend.api.new.auth.config import auth_settings


# Cookie-based authentication for web app (Mascope web-based interface)
cookie_transport = CookieTransport(
    cookie_name=auth_settings.COOKIE_NAME,
    cookie_max_age=auth_settings.COOKIE_MAX_AGE_SECONDS,
    cookie_secure=auth_settings.COOKIE_SECURE,
    cookie_httponly=auth_settings.COOKIE_HTTP_ONLY,
    cookie_samesite=auth_settings.COOKIE_SAMESITE,
)
