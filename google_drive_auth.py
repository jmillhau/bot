from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os

# Define the Google Drive API access scope (read-only)
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_google_drive():
    creds = None
    print("Checking for existing token.json file...")

    # Check if token.json exists (re-use credentials if available)
    if os.path.exists('token.json'):
        print("Found existing token.json file. Loading credentials...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials are available, initiate OAuth2 flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials are expired. Refreshing token...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Starting OAuth2 flow...")
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
            print("OAuth2 flow completed.")

        # Save the credentials for future use
        with open('token.json', 'w') as token:
            print("Saving credentials to token.json")
            token.write(creds.to_json())

    return creds

# Run authentication process
print("Starting Google Drive authentication...")
creds = authenticate_google_drive()
print("Google Drive authentication completed.")