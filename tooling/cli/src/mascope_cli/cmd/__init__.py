# flake8: noqa
from .agent import agent_app
from .backend import backend_app
from .cert import cert_app
from .dev import dev_app
from .env import env_app
from .logs import logs_app
from .prod import prod_app
from .test import test_app

# Imported after `dev` on purpose: the demo command pulls in `mascope_cli.pg`,
# which has a load-order dependency on `cmd.dev` being initialized first
# (pg.utils -> cmd.dev.docker). Importing demo earlier triggers a circular import.
from .demo import demo_app
