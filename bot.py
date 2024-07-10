import os
import discord
from discord import VoiceClient, Bot, Embed
import character_profile
from config import Config
from elevenlabs_wrapper import ElevenlabsWrapper
from openai_wrapper import OpenAiWrapper, speech_to_text_whisper
from response_modal import ResponseModal

# Initialize Bot
bot: Bot = discord.Bot()

# Initialize Config
config: Config = Config()

# Initialize AI Wrapper
elevenlabs_wrapper: ElevenlabsWrapper = ElevenlabsWrapper(config)
openai_wrapper: OpenAiWrapper = OpenAiWrapper(config)

# Initialize Profiles
profiles: dict[str, character_profile.CharacterProfile] = character_profile.load_profiles_from_yaml(
    "character_profiles.yaml")
profile_choices: list = [key for key in profiles.keys()]
current_profile: str = ""

voice_client: VoiceClient = None

can_ask: bool = True

# Check if Opus is loaded
if not discord.opus.is_loaded():
    print('opus not loaded!')
    try:
        discord.opus.load_opus(config.get_opus_location())
        print('opus successfully loaded!')
    except Exception as e:
        print(e)


@bot.event
async def on_ready():
    """
    Event that runs when the bot is ready.
    """
    print(f'We have logged in as {bot.user}')


@bot.command(description="Join the voice channel the user is currently in.")
async def join(ctx):
    """
    Command to join the voice channel the user is currently in.
    """
    global voice_client
    # The user must be in a voice channel for the bot to join
    if ctx.author.voice is None:
        await ctx.send('You need to be in a voice channel to use this command.')
        return

    channel = ctx.author.voice.channel

    # Join the voice channel
    if voice_client is None:
        voice_client = await channel.connect()

    await ctx.respond(f'Joined {channel.name}.')


@bot.command(description="Leave the current voice channel.")
async def leave(ctx):
    """
    Command to leave the current voice channel.
    """
    # Check if the bot is in a voice channel
    if ctx.voice_client is not None:
        # Leave the voice channel
        await ctx.voice_client.disconnect()
        await ctx.send('Left the voice channel.')
    else:
        await ctx.send('I am not currently in a voice channel.')


@bot.command(description="Ask a question to the bot with text")
async def ask_with_text(ctx, profile: discord.Option(str, "Choose a profile", choices=profile_choices),
                        text: discord.Option(discord.SlashCommandOptionType.string)):
    """
    Command to ask a question or talk with a bot using a specified profile.

    Parameters:
    - ctx: The context of the command.
    - profile: The chosen profile from the provided choices.
    - text: The text input for the bot to respond to.

    Functionality:
    - Checks if the provided profile exists.
    - Joins the voice channel of the user if not already connected.
    - Ensures no other request is currently being processed.
    - Clears and sets the chat history if the profile has changed.
    - Generates a response using OpenAI and plays the corresponding audio.
    """
    global voice_client
    global current_profile
    global can_ask

    # Check if the selected profile exists
    if profile not in profiles:
        return await ctx.send(f"Profile {profile} does not exist. Available profiles: {', '.join(profiles.keys())}")

    await ctx.response.defer()

    # Join the voice channel if not already connected
    if voice_client is None:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    # Check if a request is already in progress
    if not can_ask:
        return await ctx.respond("A request is currently in progress! Ask again later.")

    can_ask = False

    # Clear chat history and set system message if profile has changed
    if current_profile != profiles[profile]:
        openai_wrapper.chat_history.clear()
        openai_wrapper.chat_history.append({"role": "system", "content": profiles[profile].first_system_message})
        current_profile = profile

    # Generate response using OpenAI
    answer = openai_wrapper.chat_with_history(text)

    # Respond in text channel
    await ctx.followup.send("", embed=request_embed(text, answer))

    # Play the generated audio
    await play_audio(answer, profile)


@bot.command(description="Ask a question to the bot with your voice. Use the stop_recording command if finished")
async def ask_with_voice(ctx, profile: discord.Option(str, "Choose a profile", choices=profile_choices)):
    """
    Command to start recording audio in the voice channel for the bot to process.

    Parameters:
    - ctx: The context of the command.
    - profile: The chosen profile from the provided choices.

    Functionality:
    - Joins the voice channel of the user if not already connected.
    - Ensures no other request is currently being processed.
    - Starts recording the user's voice.
    """
    global voice_client
    global can_ask

    # Join the voice channel if not already connected
    if voice_client is None:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    # Check if a request is already in progress
    if not can_ask:
        return await ctx.respond("A request is currently in progress! Ask again later.")

    can_ask = False

    # Start recording the user's voice
    voice_client.start_recording(
        discord.sinks.MP3Sink(),  # The sink type to use.
        once_done,  # Callback function to execute once recording is done.
        ctx,  # The text channel to send the response to.
        profile  # The chosen profile for the voice interaction.
    )
    await ctx.respond("Started recording!")


async def once_done(sink: discord.sinks, ctx, profile: str):
    """
    Callback function that runs once recording is done.
    """
    global current_profile

    file_path: str = ""
    for user_id, audio in sink.audio_data.items():
        file_path = os.path.join(f"{user_id}.{sink.encoding}")
        with open(file_path, 'wb') as f:
            f.write(audio.file.read())

    question: str = speech_to_text_whisper(file_path)

    # Remove recorded file
    os.remove(file_path) if os.path.exists(file_path) else None

    if current_profile != profiles[profile]:
        openai_wrapper.chat_history.clear()
        openai_wrapper.chat_history.append({"role": "system", "content": profiles[profile].first_system_message})
        current_profile = profile

    answer: str = openai_wrapper.chat_with_history(question)

    await ctx.followup.send("", embed=request_embed(question, answer))

    # Play the audio file
    await play_audio(answer, profile)


@bot.command()
async def stop_recording(ctx):
    """
    Command to stop recording audio.
    """
    global voice_client

    if voice_client is None:
        ctx.respond("You aren't inside a voice channel!")

    voice_client.stop_recording()  # Stop recording, and call the callback (once_done).
    await ctx.delete()  # And delete.


def cleanup_request(filepath: str):
    """
    Removes the specified file if it exists and sets the global variable `can_ask` to True.

    Parameters:
    - filepath (str): The path to the file to be removed.
    """
    global can_ask

    # Remove the file if it exists
    os.remove(filepath) if os.path.exists(filepath) else None
    # Set the can_ask flag to True
    can_ask = True


def request_embed(prompt: str, answer: str) -> Embed:
    global current_profile

    embed: Embed = discord.Embed(color=discord.Colour.blurple())
    embed.add_field(name="Prompt:", value=prompt, inline=False)
    embed.add_field(name="Answer:", value=answer)
    embed.set_author(name=current_profile)

    return embed


async def play_audio(answer: str, profile: str):
    """
    Converts the given text answer to speech using Elevenlabs and plays it through the voice client in Discord.

    Parameters:
    - answer (str): The text to be converted to speech.
    - profile (str): The character profile to determine the voice used for the speech.
    """
    global voice_client

    # Generate the audio file from the text answer using the specified profile's Elevenlabs voice
    audio_file = elevenlabs_wrapper.text_to_speech_file(answer, profiles[profile].elevenlabs_voice)

    # Play the generated audio file in the voice channel
    voice_client.play(discord.FFmpegPCMAudio(audio_file, before_options='-ac 2', options='-b:a 44.1k'),
                      after=lambda x: cleanup_request(audio_file))

# Run the bot with the specified token
bot.run(config.get_bot_token())
