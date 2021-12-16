import ruamel
from ruamel.yaml import YAML
from loguru import logger


class ReadConfig():

    def __init__(self) -> None:
        pass

    def read_configfile(self, filename="cred_config.yml"):
        with open(filename) as fdesc:
            try:
                body = ruamel.yaml.round_trip_load(fdesc, preserve_quotes=True)
            except:
                logger.warning('Failed to load {filename}', filename=filename)
                return False
        return body
