from flask import current_app as app
from os import path
from googleapiclient.discovery import build
from google.oauth2 import service_account
# import google.auth
from datetime import datetime as dt
from pprint import pprint

SHARED_SHEET_ID = '1LyUFeo5in3F-IbR1eMnkp-XeQXD_zvfYraxCJBUkZPs'
LOCAL_ENV = app.config.get('LOCAL_ENV')
service_config = {
    'sheets': {
        'file': 'env/sheet_secret.json',
        'scopes': ['https://www.googleapis.com/auth/spreadsheets']
        }
}


# class MemoryCache(Cache):
#     _CACHE = {}

#     def get(self, url):
#         return MemoryCache._CACHE.get(url)

#     def set(self, url, value):
#         MemoryCache._CACHE[url] = value

#     # end class MemoryCache


def get_creds(config):
    """ Using google.oauth2.service_account to get credentials for the service account """
    app.logger.info('=========== Get Creds ====================')
    if not path.exists(config.get('file')):
        message = 'Wrong Path to Secret File'
        app.logger.info(message)
        return message
    if LOCAL_ENV is True:
        # Could add local testing credential method.
        message = "Won't work when running locally"
        app.logger.info("Won't work when running locally")
        return 'Local Test'
    credentials = service_account.Credentials.from_service_account_file(config['file'])
    app.logger.info(' tried to get credentials ')
    return credentials.with_scopes(config.get('scopes'))


def create_sheet(campaign, creds=None):
    """ Takes in an instance from the Campaign model. Get the credentials and create a worksheet. """
    print('================== create sheet =======================')
    creds = creds if creds else get_creds(service_config['sheets'])
    if isinstance(creds, str):
        return (creds, 0)
    timestamp = int(dt.timestamp(dt.now()))
    name = str(campaign.name).replace(' ', '_')
    title = f"{name}_{timestamp}"
    app.logger.info(title)
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    spreadsheet = {'properties': {'title': title}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    id = spreadsheet.get('spreadsheetId')
    app.logger.info('----------------- Spreadsheet was created? ---------------------')
    app.logger.info(f"Spreadsheet ID from create_sheet: {id}")
    spreadsheet, id = update_sheet(campaign, id=id)
    return (spreadsheet, id)


def read_sheet_full(id=SHARED_SHEET_ID, creds=None):
    """ Get the information (not the values) for a worksheet with permissions granted to our app service. """
    print('================== read sheet full =======================')
    creds = creds if creds else get_creds(service_config['sheets'])
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


def read_sheet(id=SHARED_SHEET_ID, creds=None):
    """ Read a sheet that our app service account has been given permission for. """
    id = id if id else SHARED_SHEET_ID
    print('================== read sheet =======================')
    print(id)
    creds = creds if creds else get_creds(service_config['sheets'])
    if isinstance(creds, str):
        return (creds, 0)
    service = build('sheets', 'v4', credentials=creds)
    # range_ = 'Sheet1!A1:B3'
    value_render_option = 'FORMATTED_VALUE'  # 'FORMATTED_VALUE' | 'UNFORMATTED_VALUE' | 'FORMULA'
    date_time_render_option = 'FORMATTED_STRING'  # 'FORMATTED_STRING' | 'SERIAL_NUMBER'
    major_dimension = 'ROWS'  # 'ROWS' | 'COLUMNS'
    request = service.spreadsheets().values().get(
        spreadsheetId=id,
        # range=range_,
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
    print('------------------ Spreadsheet print ---------------------')
    pprint(spreadsheet)
    return (spreadsheet, id)


def clean(obj):
    """ Make sure this obj is serializable. Datetime objects should be turned to strings. """
    if isinstance(obj, dt):
        return obj.isoformat()
    return obj


def get_vals(campaign):
    """ Get the values we want to put into our worksheet report """
    default = [["pizza", "burger"], [1004, 312], ['good', 'okay']]
    brands = ['Brand', ', '.join([ea.name for ea in campaign.brands])]
    users = ['Influencer', ', '.join([ea.name for ea in campaign.users])]
    columns = campaign.report_columns()
    results = [[clean(getattr(post, ea, '')) for ea in columns] for post in campaign.posts]
    # all fields need to be serializable, which means all datetime fields should be changed to strings.
    # data = request.form.to_dict(flat=False)['related']
    # app.logger.info(data)
    app.logger.info(brands)
    app.logger.info(users)
    app.logger.info(columns)
    app.logger.info('------------------------')
    app.logger.info(len(results))
    app.logger.info('=========================')
    sheet_rows = [brands, users, [''], columns, *results]
    return sheet_rows if sheet_rows else default


def compute_A1(arr2d, start='A1', sheet='Sheet1'):
    """ Determine A1 format for 2D-array input, on given sheet, starting at given cell """
    row_count = len(arr2d)
    col_count = len(max(arr2d, key=len))
    # TODO: write regex that separates the letter and digit sections. 'A1' would have following result:
    col, row = 'A', 1
    final_col = chr(ord(col) + col_count)
    final_row = row_count + row
    app.logger.info(f"Row Count: {row_count}, Column Count: {col_count}")
    return f"{sheet}!{start}:{final_col}{final_row}"


def update_sheet(campaign, id=SHARED_SHEET_ID, creds=None):
    """ Get the data we want, then append it to the worksheet """
    print('================== update sheet =======================')
    creds = creds if creds else get_creds(service_config['sheets'])
    if isinstance(creds, str):
        return (creds, 0)
    service = build('sheets', 'v4', credentials=creds)
    value_input_option = 'USER_ENTERED'  # 'RAW' | 'USER_ENTERED' | 'INPUT_VALUE_OPTION_UNSPECIFIED'
    insert_data_option = 'OVERWRITE'  # 'OVERWITE' | 'INSERT_ROWS'
    major_dimension = 'ROWS'  # 'ROWS' | 'COLUMNS'
    vals = get_vals(campaign)
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
    print('---------- Update Done? ----------------')
    pprint(spreadsheet)
    return (spreadsheet, id)
