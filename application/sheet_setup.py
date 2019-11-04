# from google.auth import app_engine  # does not work in python 3
# from google.cloud import sheets
from os import environ, path  # path Used by both quickstart and Common code method.
from googleapiclient.discovery import build
# from googleapiclient._auth import with_scopes
from google.oauth2 import service_account

# from httplib2 import Http                     # Google API Common Code Walk Through
# from oauth2client import file, client, tools  # Google API Common Code Walk Through
# from google_auth_oauthlib.flow import Flow
import google.auth
# from google_auth_oauthlib import get_user_credentials
# from google-auth-oauthlib import get_user_credentials, flow
# https://google-auth-oauthlib.readthedocs.io/en/stable/reference/google_auth_oauthlib.flow.html

CLIENT_SECRET_FILE = 'env/client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CLIENT_ID = environ.get('CLIENT_ID')
CLIENT_SECRET = environ.get('CLIENT_SECRET')
SHEET_EMAIL = environ.get('SHEET_EMAIL')
SHEET_NAME = environ.get('SHEET_NAME')
SHEET_SECRET = environ.get('SHEET_SECRET')


def get_creds():
    """ This approach based on Google API common code walkthrough """
    STORAGE = 'env/storage.json'
    if not path.exists(STORAGE):
        raise EnvironmentError('Missing file')
    service = None
    # credentials = get_user_credentials(SCOPES, CLIENT_ID, CLIENT_SECRET)
    # flow = flow.Flow.from_client_secrets_file(CLIENT_SECRET, scopes=SCOPES)  # redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    # auth_url, _ = flow.authorization_url(prompt='consent')
    # store = file.Storage(STORAGE)
    # creds = store.get()
    # if not creds or creds.invalid:
    #     flow = client.flow_from_clientsecrets(CLIENT_SECRET, SCOPES)
    #     creds = tools.run_flow(flow, store)
    # service = build('sheets', 'v4', http=creds.authorize(Http()))
    # service = build('sheets', 'v4')  # , http=creds.authorize(Http()))
    return service


def get_sheet(local_env):
    """ Get the credentials and create a worksheet. """
    print('======================= Called get_sheet =========================')
    if not path.exists(CLIENT_SECRET_FILE):
        test_string = 'Wrong Path to Secret File'
        print(test_string)
        return test_string
    if local_env is True:
        return 'Local Test'
    # creds = app_engine.Credentials(scopes=SCOPES)
    # creds, _ = google.auth.default()  # the default creds do not work, cannot be given correct scope
    # cred_scopes = with_scopes(creds, SCOPES)
    credentials = service_account.Credentials.from_service_account_file(CLIENT_SECRET_FILE)
    print('credentials returned') if credentials else print('ERROR ON credentials')
    creds = credentials.with_scopes(SCOPES)
    # creds = sheets.Client()
    # creds = get_user_credentials(SCOPES, CLIENT_ID, CLIENT_SECRET)
    test_string = 'We got creds!' if creds else 'No creds yet.'
    print(test_string)
    print(creds)
    # service = build('sheets', 'v4', credentials=creds)
    service = build('sheets', 'v4', credentials=creds)
    test_string = 'We got a service!' if service else 'Creds and service did not work.'
    print(test_string)
    title = 'social-test'
    spreadsheet = {'properties': {'title': title}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                fields='spreadsheetId').execute()
    # "Request had insufficient authentication scopes."
    id = spreadsheet.get('spreadsheetId')
    print('Spreadsheet ID: {0}'.format(id))
    return spreadsheet
# response = service.something
