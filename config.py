import configparser
import os


class Config:
    config = configparser.ConfigParser()
    config_file_path = None

    def __init__(self, config_file_path='~/.vbot.cfg'):
        self.config_file_path = os.path.expanduser(config_file_path)
        self.load_config()

    def load_config(self):
        # Load configuration parameters
        if os.path.exists(self.config_file_path):
            self.config.read(self.config_file_path)
        else:
            self.set_default_config()

    def set_default_config(self):
        # Set default configuration'
        self.config['telegram'] = {}
        self.config['telegram']['bot_token'] = ''
        self.config['telegram']['vote_channel'] = '-100111111111'
        self.config['mysql'] = {}
        self.config['mysql']['host'] = 'localhost'
        self.config['mysql']['database'] = 'vbot'
        self.config['mysql']['user'] = 'root'
        self.config['mysql']['password'] = ''

        with open(self.config_file_path, 'w') as config_file:
            self.config.write(config_file)

    def get(self):
        # Obtain configuration
        return self.config
