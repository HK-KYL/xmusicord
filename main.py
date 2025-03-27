import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import os
import requests
from collections import deque

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # Load token from .env file
if DISCORD_TOKEN is None:
    print("Error: DISCORD_TOKEN is not set. Check your Railway environment variables!")
    exit(1)

LYRICS_API = "https://api.lyrics.ovh/v1"  # Using Lyrics.ovh API

intents = discord.Intents.default()
intents.message_content = True  # Required for command handling
bot = commands.Bot(command_prefix="!", intents=intents)
queue = deque()
vc = None
song_queue = deque()  # Renamed the queue to song_queue

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

async def play_next(ctx):
    global vc
    if song_queue:  # Changed from queue to song_queue
        url, title = song_queue.popleft()
        vc.play(discord.FFmpegPCMAudio(url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'Now playing: {title}')
    else:
        await vc.disconnect()
        vc = None

@bot.command()
async def play(ctx, *, query: str):
    """Play a song from YouTube by keyword or URL"""
    global vc
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("You need to be in a voice channel!")
        return
    
    if not vc or not vc.is_connected():
        vc = await voice_channel.connect()
    
    ydl_opts = {'format': 'bestaudio'}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f'ytsearch:{query}', download=False)['entries'][0]
        url = info['url']
        title = info['title']
    
    song_queue.append((url, title))  # Changed from queue.append to song_queue.append
    if not vc.is_playing():
        await play_next(ctx)
    else:
        await ctx.send(f'Added to queue: {title}')

@bot.command()
async def skip(ctx):
    """Skip the current song"""
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("Skipped song!")

@bot.command()
async def queue(ctx):
    """Show the song queue"""
    if song_queue:  # Changed from queue to song_queue
        queue_list = '\n'.join([f'{i+1}. {title}' for i, (_, title) in enumerate(song_queue)])
        await ctx.send(f'Queue:\n{queue_list}')
    else:
        await ctx.send("Queue is empty!")

@bot.command()
async def stop(ctx):
    """Stop playback and disconnect"""
    global vc
    if vc:
        await vc.disconnect()
        vc = None
        song_queue.clear()
        await ctx.send("Stopped playback and disconnected!")

@bot.command()
async def lyrics(ctx):
    """Fetch lyrics for the currently playing song"""
    if not vc or not vc.is_playing():
        await ctx.send("No song is currently playing!")
        return
    
    current_song = song_queue[0][1] if song_queue else "Unknown"
    artist, title = current_song.split(" - ", 1) if " - " in current_song else ("", current_song)
    response = requests.get(f'{LYRICS_API}/{artist}/{title}')
    if response.status_code == 200:
        lyrics = response.json().get("lyrics", "Lyrics not found!")
        await ctx.send(f'**Lyrics for {current_song}:**\n{lyrics[:2000]}')  # Discord message limit
    else:
        await ctx.send("Could not fetch lyrics!")

@bot.command()
async def karaoke(ctx):
    """Toggle karaoke mode (masked lyrics)"""
    await ctx.send("Karaoke mode is not implemented yet!")

bot.run(DISCORD_TOKEN)
