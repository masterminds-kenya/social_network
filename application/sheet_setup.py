from google.auth import app_engine
from googleapiclient.discovery import build


SCOPES = ['']
credentials = app_engine.Credentials(scopes=SCOPES)
service = build('', '', credentials=credentials)
# response = service.something