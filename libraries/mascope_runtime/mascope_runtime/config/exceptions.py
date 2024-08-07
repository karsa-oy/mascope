class MascopeConfigNotFoundException(Exception):
    def __init__(self, runtime):
        super().__init__(
            f"""
    Runtime '{runtime["name"]}' is active but is
    missing a configuration file. Please make sure
    that a valid Mascope config file called 
    'mascope.toml' is placed in the runtime path:
    
        '{runtime["path"]}'
    """
        )
