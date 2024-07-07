import yaml


class CharacterProfile:
    def __init__(self, elevenlabs_voice, first_system_message):
        self.elevenlabs_voice = elevenlabs_voice
        self.first_system_message = first_system_message


def load_profiles_from_yaml(file_path: str) -> dict[str, CharacterProfile]:
    with open(file_path, 'r') as file:
        profiles_data = yaml.safe_load(file)
    profiles = {}
    for key, data in profiles_data['profiles'].items():
        profiles[key] = CharacterProfile(
            data['elevenlabs_voice'],
            data['first_system_message']
        )
    return profiles
