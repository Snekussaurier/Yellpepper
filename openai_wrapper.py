import whisper
from config import Config
from openai import OpenAI
import tiktoken
from rich import print

# Load the Whisper model
model = whisper.load_model("base")


def num_tokens_from_messages(messages: list, modelgpt: str = 'gpt-3.5'):
    """
    Returns the number of tokens used by a list of messages.
    This is useful for managing token limits in OpenAI's GPT models.

    Parameters:
    - messages (list): A list of messages in the format required by OpenAI's API.
    - modelgpt (str): The name of the GPT model being used (default is 'gpt-3.5').

    Returns:
    - int: The total number of tokens used by the messages.
    """
    try:
        encoding = tiktoken.encoding_for_model(modelgpt)
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # If there's a name, the role is omitted
                    num_tokens += -1  # Role is always required and always 1 token
        num_tokens += 2  # Every reply is primed with <im_start>assistant
        return num_tokens
    except Exception:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {modelgpt}. 
        See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted 
        to tokens.""")


def speech_to_text_whisper(filepath: str) -> str:
    """
    Transcribes speech to text using the Whisper model.

    Parameters:
    - filepath (str): The path to the audio file to be transcribed.

    Returns:
    - str: The transcribed text.
    """
    result = model.transcribe(filepath)
    return result["text"]


class OpenAiWrapper:
    def __init__(self, config: Config):
        """
        Initializes the OpenAiWrapper with the given configuration.

        Parameters:
        - config (Config): The configuration object containing API keys and settings.
        """
        self.chat_history = []  # Stores the entire conversation
        self.openai_client = OpenAI(api_key=config.get_openai_api_key())

    def chat_with_history(self, prompt: str = "") -> str:
        """
        Sends a prompt to the OpenAI GPT model and returns the response, maintaining chat history.

        Parameters:
        - prompt (str): The prompt/question to send to the GPT model.

        Returns:
        - str: The response from the GPT model.
        """
        if not prompt:
            print("Didn't receive input!")
            return ""

        # Add the prompt to the chat history
        self.chat_history.append({"role": "user", "content": prompt})

        # Check total token limit and remove old messages if necessary
        print(f"[coral]\nChat History has a current token length of {num_tokens_from_messages(self.chat_history)}")
        while num_tokens_from_messages(self.chat_history) > 8000:
            self.chat_history.pop(1)  # Skip the 1st message since it's the system message
            print(f"Popped a message! New token length is: {num_tokens_from_messages(self.chat_history)}")

        print("[yellow]\nAsking ChatGPT a question...")
        completion = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.chat_history
        )

        # Add the response to the chat history
        self.chat_history.append(
            {"role": completion.choices[0].message.role, "content": completion.choices[0].message.content}
        )

        # Process and print the answer
        openai_answer = completion.choices[0].message.content
        print(f"[green]\n{openai_answer}\n")
        return openai_answer
