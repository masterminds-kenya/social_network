from google.auth import app_engine  # does not work in python 3
# from google.cloud import sheets
from googleapiclient.discovery import build


def get_sheet(local_env):
    """ Get the credentials and create a worksheet. """
    print('Called get_sheet')
    if local_env is True:
        return 'Local Test'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = app_engine.Credentials(scopes=SCOPES)
    # creds = sheets.Client()
    test_string = 'We got creds!' if creds else 'Creds did not work.'
    print(test_string)
    service = build('sheets', 'v4', credentials=creds)
    test_string = 'We got a service!' if service else 'Creds and service did not work.'
    print(test_string)
    title = 'social-test'
    spreadsheet = {'properties': {'title': title}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                fields='spreadsheetId').execute()
    id = spreadsheet.get('spreadsheetId')
    print('Spreadsheet ID: {0}'.format(id))
    return spreadsheet
# response = service.something


def test():
    """ This is just a test function """
    print('You called the test function!')
    return 'Test Return'
