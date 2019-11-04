# from google.auth import app_engine  # does not work in python 3
# from google.cloud import sheets
import os.path      # Used by both quickstart and Common code method.
from googleapiclient.discovery import build
# from httplib2 import Http                     # Google API Common Code Walk Through
# from oauth2client import file, client, tools  # Google API Common Code Walk Through
# from google-auth-oauthlib import
CLIENT_SECRET = 'env/client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_creds():
    """ This approach based on Google API common code walkthrough """
    STORAGE = 'env/storage.json'
    if not os.path.exists(STORAGE):
        raise EnvironmentError('Missing file')
    service = None
    # store = file.Storage(STORAGE)
    # creds = store.get()
    # if not creds or creds.invalid:
    #     flow = client.flow_from_clientsecrets(CLIENT_SECRET, SCOPES)
    #     creds = tools.run_flow(flow, store)
    # service = build('sheets', 'v4', http=creds.authorize(Http()))
    return service


def get_sheet(local_env):
    """ Get the credentials and create a worksheet. """
    print('======================= Called get_sheet =========================')
    if local_env is True:
        return 'Local Test'
    # creds = app_engine.Credentials(scopes=SCOPES)
    creds = None
    # creds = sheets.Client()
    test_string = 'We got creds!' if creds else 'No creds yet.'
    print(test_string)
    # service = build('sheets', 'v4', credentials=creds)
    service = build('sheets', 'v4')
    test_string = 'We got a service!' if service else 'Creds and service did not work.'
    print(test_string)
    print(service)
    title = 'social-test'
    spreadsheet = {'properties': {'title': title}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                fields='spreadsheetId').execute()
    # "Request had insufficient authentication scopes."
    id = spreadsheet.get('spreadsheetId')
    print('Spreadsheet ID: {0}'.format(id))
    return spreadsheet
# response = service.something
