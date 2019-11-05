from os import path
from googleapiclient.discovery import build
from google.oauth2 import service_account
# import google.auth

service_config = {
    'sheets': {
        'file': 'env/sheet_secret.json',
        'scopes': ['https://www.googleapis.com/auth/spreadsheets']
        }
}


def get_creds(local_env, config):
    """ Using google.oauth2.service_account to get credentials for the service account """
    if not path.exists(config.get('file')):
        return 'Wrong Path to Secret File'
    if local_env is True:
        # Could add local testing credential method.
        return 'Local Test'
    credentials = service_account.Credentials.from_service_account_file(config['file'])
    return credentials.with_scopes(config.get('scopes'))


def create_sheet(local_env, title):
    """ Get the credentials and create a worksheet. """
    print('================== create sheet =======================')
    creds = get_creds(local_env, service_config['sheets'])
    if isinstance(creds, str):
        return (creds, 0)
    service = build('sheets', 'v4', credentials=creds)
    spreadsheet = {'properties': {'title': title}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    id = spreadsheet.get('spreadsheetId')
    print('Spreadsheet ID: {0}'.format(id))
    return (spreadsheet, id)
