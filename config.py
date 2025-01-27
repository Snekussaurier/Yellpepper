import yaml
import os


class Config:
    def __init__(self, config_file='config.yaml'):
        self.config_file = config_file
        self.config = self.read_config()

    def read_config(self):
        with open(self.config_file, 'r') as file:
            config_content = file.read()
            # Replace placeholders with environment variables
            config_content = os.path.expandvars(config_content)
            return yaml.safe_load(config_content)

    def get_bot_token(self):
        return self.config['DISCORD_BOT_TOKEN']

    def get_opus_location(self):
        return self.config['OPUS_LOCATION']

    def get_eleven_labs_api_key(self):
        return self.config['ELEVEN_LABS_API_KEY']

    def get_openai_api_key(self):
        return self.config['OPENAI_API_KEY']