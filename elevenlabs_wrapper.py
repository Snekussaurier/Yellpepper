from config import Config
import uuid
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs


class ElevenlabsWrapper:

    def __init__(self, config: Config):
        self.ELEVENLABS_API_KEY = config.get_eleven_labs_api_key()
        self.elevenLabsClient = ElevenLabs(
            api_key=self.ELEVENLABS_API_KEY,
        )

    def text_to_speech_file(self, text: str, voice_id: str) -> str:
        # Calling the text_to_speech conversion API with detailed parameters
        response = self.elevenLabsClient.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_44100_64",
            text=text,
            model_id="eleven_multilingual_v2",
            # use the turbo model for low latency, for other languages use the `eleven_multilingual_v2`
            voice_settings=VoiceSettings(
                stability=0.35,
                similarity_boost=0.75,
                style=0.35,
                use_speaker_boost=False,
            ),
        )

        # Generating a unique file name for the output MP3 file
        save_file_path: str = f"{uuid.uuid4()}.mp3"

        # Writing the audio to a file
        with open(save_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        print(f"{save_file_path}: A new audio file was saved successfully!")

        # Return the path of the saved audio file
        return save_file_path
