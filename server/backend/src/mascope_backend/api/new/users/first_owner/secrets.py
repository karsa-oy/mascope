from mascope_backend.runtime import runtime


server_owner_secret_key = runtime.secret(
    "SERVER_OWNER_SECRET_KEY_FILE", "server_owner_secret_key.txt"
)
