from dotenv import load_dotenv
import uvicorn
import os

#from backend.api import *  # noqa - import ensures api is instantiated

load_dotenv(dotenv_path="../.env.development")

api_port = int(os.environ.get('MASCOPE_PUBLIC_API_PORT'))
mode = os.environ.get('MASCOPE_PUBLIC_MODE')


def run():
    uvicorn.run(
        'backend.server:app',
        port=api_port,
        reload=(mode == 'development')
    )
