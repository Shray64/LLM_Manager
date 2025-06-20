import os
import re
import yaml
import pkg_resources

def load_config(config_path=None):
    """Load and process the configuration file"""
    if config_path is None:
        config_path = pkg_resources.resource_filename('llm_manager', 'config.yaml')
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    return substitute_env_vars(config)

def substitute_env_vars(config):
    """Replace ${VAR_NAME:-default} patterns with environment variables or defaults"""
    if isinstance(config, dict):
        return {k: substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_env_vars(i) for i in config]
    elif isinstance(config, str) and "${" in config:
        pattern = r'\${([^}^:]+)(?::-([^}]+))?}'
        match = re.search(pattern, config)
        if match:
            env_var, default = match.groups()
            value = os.environ.get(env_var, default or "")
            return config.replace(match.group(0), value)
    return config
