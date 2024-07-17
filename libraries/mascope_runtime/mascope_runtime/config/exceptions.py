
def instructions(config_dir):
    return f"""
    Please ensure that config files are:
    1. Placed in your 'MASCOPE_PATH' config directory:
        '{config_dir}'
    2. Named 'mascope.<name>.toml' where '<name>' includes only 
        alphanumeric characters and underscores
    3. Identified using a standard '<name>' of 'prod' or 'dev',
        or by passing a mascope CLI as an argument:
        'mascope --config <name> ...'
    """

class MascopeMissingPathException(Exception):
    def __init__(self):
        super().__init__(f"""

    MASCOPE_PATH environment variable is not set: please set it with to 
    a path containing a valid Mascope runtime directory.

    If you are a Mascope user, contact your Mascope server administrator.

    If you are a Mascope developer, this path can point to your local clone
    of the Mascope git repo. See the README.md for more information.
    """)

class MascopeConfigNotResolvedException(Exception):
    def __init__(self, config_dir):
        super().__init__(f"""

    Mascope was not able to resolve a configuration file.

    {instructions(config_dir)}
    """)

class MascopeConfigNotFoundException(Exception):
    def __init__(self, config_dir, config_name):
        super().__init__(f"""

    Mascope was not able to find the configuration file.
    
    The '{config_name}' configuration was selected, but no file
    named 'mascope.{config_name}.toml' was found in the 'MASCOPE_PATH'
    config directory:
    
        '{config_dir}'

    {instructions(config_dir)}
    """)