from mascope_backend.runtime import runtime


jwt_secret_key = runtime.secret("JWT_SECRET_KEY_FILE", "jwt_secret_key.txt")
