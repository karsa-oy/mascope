import os

SERVER_OWNER_SECRET_KEY_DEV = "NeverGonnaLetYouDown87"

server_owner_secret_file = os.environ.get("SERVER_OWNER_SECRET_KEY_FILE")
if server_owner_secret_file:
    with open(server_owner_secret_file, "r", encoding="utf-8") as f:
        server_owner_secret_key = f.readlines()[0].replace("\n", "")
else:
    server_owner_secret_key = SERVER_OWNER_SECRET_KEY_DEV
