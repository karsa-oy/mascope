import os
import re
import yaml


def load_env_yaml(yaml_file):
    env_pattern = re.compile(r".*?\${(.*?)}.*?")
    def env_constructor(loader, node):
        value = loader.construct_scalar(node)
        for group in env_pattern.findall(value):
            value = value.replace(f"${{{group}}}", os.environ.get(group))
        return value
    yaml.add_implicit_resolver("!pathex", env_pattern)
    yaml.add_constructor("!pathex", env_constructor)
    with open(yaml_file, 'r') as f:
        res = yaml.load(f.read(), Loader=yaml.FullLoader)
    return res