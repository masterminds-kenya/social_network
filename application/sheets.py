from os import path
from googleapiclient.discovery import build
from google.oauth2 import service_account
# import google.auth

SHARED_SHEET_ID = '1LyUFeo5in3F-IbR1eMnkp-XeQXD_zvfYraxCJBUkZPs'
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
    # print('Spreadsheet ID: {0}'.format(id))
    return (spreadsheet, id)


def read_sheet_full(local_env, id=SHARED_SHEET_ID):
    """ Get the information (not the values) for a worksheet with permissions granted to our app service. """
    from pprint import pprint
    print('================== read sheet =======================')
    creds = get_creds(local_env, service_config['sheets'])
    if isinstance(creds, str):
        return (creds, 0)
    service = build('sheets', 'v4', credentials=creds)
    ranges = ['Sheet1!A1:B3']
    include_grid_data = True  # Ignored if a field mask was set in the request.
    request = service.spreadsheets().get(spreadsheetId=id, ranges=ranges, includeGridData=include_grid_data)
    spreadsheet = request.execute()
    id = spreadsheet.get('spreadsheetId')
    pprint(spreadsheet)
    return (spreadsheet, id)


def read_sheet(local_env, id=SHARED_SHEET_ID):
    """ Read a sheet that our app service account has been given permission for. """
    # from pprint import pprint
    id = id if id else SHARED_SHEET_ID
    print('================== read sheet values =======================')
    print(id)
    creds = get_creds(local_env, service_config['sheets'])
    if isinstance(creds, str):
        return (creds, 0)
    service = build('sheets', 'v4', credentials=creds)
    range_ = 'Sheet1!A1:B3'
    value_render_option = 'FORMATTED_VALUE'  # 'FORMATTED_VALUE' | 'UNFORMATTED_VALUE' | 'FORMULA'
    date_time_render_option = 'FORMATTED_STRING'  # 'FORMATTED_STRING' | 'SERIAL_NUMBER'
    major_dimension = 'ROWS'  # 'ROWS' | 'COLUMNS'
    request = service.spreadsheets().values().get(
        spreadsheetId=id,
        range=range_,
        valueRenderOption=value_render_option,
        dateTimeRenderOption=date_time_render_option,
        majorDimension=major_dimension
        )
    spreadsheet = request.execute()
    sheet_vals = spreadsheet.get('values')
    if sheet_vals:
        for row in sheet_vals:
            print(', '.join(row))
    id = spreadsheet.get('spreadsheetId')
    # pprint(spreadsheet)
    return (spreadsheet, id)


def get_vals():
    """ Get the values we want to put into our worksheet report """
    default = [["pizza", "burger"], [1004, 312], ['good', 'okay']]

    return default


def compute_A1(arr2d, start='A1', sheet='Sheet1'):
    """ Determine A1 format for 2D-array input, on given sheet, starting at given cell """
    row_count = len(arr2d)
    col_count = len(max(arr2d, key=len))
    # TODO: write regex that separates the letter and digit sections. 'A1' would have following result:
    col, row = 'A', 1
    final_col = chr(ord(col) + col_count)
    final_row = row_count + row
    return f"{sheet}!{start}:{final_col}{final_row}"


def update_sheet(local_env, id=SHARED_SHEET_ID):
    """ Get the data we want, then append it to the worksheet """
    # from pprint import pprint
    print('================== update sheet =======================')
    creds = get_creds(local_env, service_config['sheets'])
    if isinstance(creds, str):
        return (creds, 0)
    service = build('sheets', 'v4', credentials=creds)
    value_input_option = 'USER_ENTERED'  # 'RAW' | 'USER_ENTERED' | 'INPUT_VALUE_OPTION_UNSPECIFIED'
    insert_data_option = 'OVERWRITE'  # 'OVERWITE' | 'INSERT_ROWS'
    major_dimension = 'ROWS'  # 'ROWS' | 'COLUMNS'
    vals = get_vals()
    range_ = compute_A1(vals) or 'Sheet1!A1:B2'

    value_range_body = {
        "majorDimension": major_dimension,
        "range": range_,
        "values": vals
    }
    request = service.spreadsheets().values().append(
        spreadsheetId=id,
        range=range_,
        valueInputOption=value_input_option,
        insertDataOption=insert_data_option,
        body=value_range_body
        )
    spreadsheet = request.execute()
    id = spreadsheet.get('spreadsheetId')
    # pprint(spreadsheet)
    return (spreadsheet, id)
