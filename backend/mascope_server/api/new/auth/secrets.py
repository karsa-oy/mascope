import os

JWT_SECRET_KEY_DEV = "NeverGonnaGiveYouUp42"

jwt_secret_file = os.environ.get("JWT_SECRET_KEY_FILE")
if jwt_secret_file:
    f = open(jwt_secret_file, "r")
    jwt_secret_key = f.readlines()[0].replace("\n", "")
else:
    jwt_secret_key = JWT_SECRET_KEY_DEV
