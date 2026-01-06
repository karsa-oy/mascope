from fastapi_users.authentication import BearerTransport


# Bearer-based transport for access token authentication in the Jupyter server
access_token_transport = BearerTransport(tokenUrl="/api/auth/access_token/generate")
