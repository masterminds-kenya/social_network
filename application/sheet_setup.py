from google.auth import app_engine
from googleapiclient.discovery import build


def get_sheet(local_env):
    """ Get the credentials and create a worksheet. """
    if local_env is True:
        return 'Local Test'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = app_engine.Credentials(scopes=SCOPES)
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
