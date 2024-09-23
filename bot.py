import discord
from openai import OpenAI
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_drive_auth import authenticate_google_drive  # Import Google Drive authentication
import io

# Load environment variables from .env file
load_dotenv()

# Set your API keys from environment variables
  # Load OpenAI API key from environment variable
discord_token = os.getenv('DISCORD_TOKEN')    # Load Discord bot token from environment variable
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Authenticate with Google Drive
creds = authenticate_google_drive()

# Function to list files in a specific Google Drive folder and find the FAQ file
def find_faq_file_in_folder(folder_id, creds):
    service = build('drive', 'v3', credentials=creds)

    # Query for files in the specified folder
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, pageSize=100, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])

    faq_file_id = None

    # Search for the FAQ file by name (case-insensitive)
    for file in files:
        if "faq" in file['name'].lower():  # Customize to match part of your FAQ file name
            faq_file_id = file['id']
            print(f"Found FAQ file: {file['name']} with ID: {file['id']}")
            break

    return faq_file_id

# Function to download the FAQ file from Google Drive
def download_faq_file(file_id, creds):
    service = build('drive', 'v3', credentials=creds)

    # Export the file as a plain text file (for Google Docs/Sheets)
    request = service.files().export_media(fileId=file_id, mimeType='text/plain')

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")

    # Return the file content as a string
    return fh.getvalue().decode('utf-8')

# Function to search the FAQ document for an answer
def search_faq(question, faq_content):
    question = question.lower()
    lines = faq_content.split('\n')  # Split the FAQ content into lines
    answer = None

    # Search for the question in the FAQ content
    for i, line in enumerate(lines):
        if question in line.lower():
            # Get the answer (next line after the question)
            answer = lines[i + 1] if i + 1 < len(lines) else "Sorry, I can't find the answer to that."
            break

    return answer

# Function to generate a conversational response using OpenAI
def generate_conversational_response(user_input):
    response = OpenAI.completions.create(engine="gpt-3.5-turbo-instruct",
    prompt=f"Respond to this in a conversational tone: {user_input}",
    max_tokens=150)
    return response.choices[0].text.strip()

# Start of the bot
intents = discord.Intents.default()  # Create a new instance of the default intents
intents.message_content = True       # Enable the bot to read the message content

client = discord.Client(intents=intents)

# On bot startup, search the folder for the FAQ file and load it
@client.event
async def on_ready():
    folder_id = '1HtBcRQm1tiVVZyLpOPsXxFM0JwFLuqYM'  # Replace with your actual folder ID
    faq_file_id = find_faq_file_in_folder(folder_id, creds)

    if faq_file_id:
        global faq_content
        faq_content = download_faq_file(faq_file_id, creds)
        print(f"FAQ Content Loaded:\n{faq_content[:500]}")  # Print the first 500 characters of the FAQ
    else:
        print("FAQ file not found in the specified folder.")

    print(f'We have logged in as {client.user}')

# Handle incoming messages
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # General conversational response using OpenAI
    if message.content.startswith('!ask'):
        user_input = message.content[len('!ask '):].strip()
        response = generate_conversational_response(user_input)
        await message.channel.send(response)

    # Search FAQ for employee question
    if message.content.startswith('!faq'):
        question = message.content[len('!faq '):].strip()
        answer = search_faq(question, faq_content)
        await message.channel.send(answer)

# Run the bot
client.run(discord_token)