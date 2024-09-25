import discord
from openai import OpenAI
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_drive_auth import authenticate_google_drive  # Import Google Drive authentication
import io
from discord import Message

# Load environment variables from .env file
load_dotenv()

# Set your API keys from environment variables
  # Load OpenAI API key from environment variable
discord_token = os.getenv('DISCORD_TOKEN')    # Load Discord bot token from environment variable
ai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
        
    if answer is None or answer.strip() == "":
        answer = "Sorry, I can't find the answer to that."
    return answer

def search_faq_ai(question, faq_content):
    try:
        response = ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                # {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided FAQ content. If the answer is not in the FAQ, respond with exactly: 'Sorry, I can't find the answer to that.'"},
                 {"role": "system", "content": """You are a helpful assistant that finds answers in the provided FAQ content. 
                Your task is to match questions, even if they are phrased differently or are only part of a larger question in the FAQ.
                When you find a match, focus on answering only the specific part asked by the user.
                If the answer in the FAQ covers multiple topics, extract and return only the relevant part.
                If you can't find a matching question or answer in the FAQ, respond with exactly: 'Sorry, I can't find the answer to that.'
                
                Example:
                FAQ Content:
                Q: Do you offer open play or walk-ins or drop-ins?
                A: We do not offer any walk-in events. We have scheduled Open Play nights for Adult participants only 18+. For more information on those, see our Open Play page here.
                
                User Question: "Do you offer drop-ins?"
                Your Response: "We do not offer any walk-in events."
                
                Always ensure your response is concise and directly addresses the user's specific question."""},
                {"role": "user", "content": f"FAQ Content:\n\n{faq_content}\n\nQuestion: {question}\n\nAnswer:"}
            ],
            max_tokens=200,
            temperature=0.3,
            stream=False,
        )
        answer = response.choices[0].message.content.strip()
        
        if answer.startswith("Answer:"):
            answer = answer[7:].strip()
    
        if answer is None or answer.strip() == "":
            answer = "Sorry, I can't find the answer to that."
        return answer
    except Exception as e:
        print(f"Error in search_faq: {str(e)}")
        return "I'm sorry, but I encountered an error while searching for the answer. Please try again later."

# Function to generate a conversational response using OpenAI
def generate_conversational_response(user_input):
    response = ai_client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=f"Respond to this in a conversational tone: {user_input}",
        max_tokens=150,
        stream=False,
    )
    return response.choices[0].text.strip()

# Start of the bot
intents = discord.Intents.default()  # Create a new instance of the default intents
intents.message_content = True       # Enable the bot to read the message content

discord_client = discord.Client(intents=intents)  # Create a new instance of the Discord client

# On bot startup, search the folder for the FAQ file and load it
@discord_client.event
async def on_ready():
    folder_id = '1HtBcRQm1tiVVZyLpOPsXxFM0JwFLuqYM'  # Replace with your actual folder ID
    faq_file_id = find_faq_file_in_folder(folder_id, creds)

    if faq_file_id:
        global faq_content
        faq_content = download_faq_file(faq_file_id, creds)
        print(f"FAQ Content Loaded:\n{faq_content[:500]}")  # Print the first 500 characters of the FAQ
    else:
        print("FAQ file not found in the specified folder.")

    print(f'We have logged in as {discord_client.user}')

# Handle incoming messages
@discord_client.event
async def on_message(message: Message):
    if message.author == discord_client.user:
        return
    try:
        # General conversational response using OpenAI
        if message.content.startswith('!ask'):
            user_input = message.content[len('!ask '):].strip()
            response = generate_conversational_response(user_input)
            await message.channel.send(response)
    
        # Search FAQ for employee question        
        if message.content.startswith('!faq-old'):
            question = message.content[len('!faq '):].strip()
            answer = search_faq(question, faq_content)
            await message.channel.send(answer)
        elif message.content.startswith('!faq'):
            question = message.content[len('!faq '):].strip()
            answer = search_faq_ai(question, faq_content)
            await message.channel.send(answer)
            
    except Exception as e:
        print(f"Error: {str(e)}")

# Run the bot
discord_client.run(discord_token)