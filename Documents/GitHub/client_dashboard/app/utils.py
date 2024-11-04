import yaml

def load_api_keys(config_path='config/config.yaml'):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)
