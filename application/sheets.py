from flask import flash, current_app as app
from flask_login import current_user
from os import path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime as dt
import re
# from pprint import pprint  # Only used for debugging.

SHARED_SHEET_ID = ''
service_config = {
    'sheets': {
        'file': 'env/sheet_secret.json',
        'scopes': ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        }
}


def get_creds(config):
    """ Using google.oauth2.service_account to get credentials for the service account """
    creds = None
    if not path.exists(config.get('file')):
        message = 'Wrong Path to Secret File'
        app.logger.error(message)
        raise FileNotFoundError(message)
    if app.config.get('LOCAL_ENV') is True:  # Could add local testing credential method.
        message = "Won't work when running locally"
        app.logger.error(message)
        raise EnvironmentError(message)
    try:
        credentials = service_account.Credentials.from_service_account_file(config['file'])
    except Exception as e:
        app.logger.error("Could not get credentials")
        app.logger.error(e)
    try:
        creds = credentials.with_scopes(config.get('scopes'))
    except Exception as e:
        app.logger.error("Could not get Scopes for credentials")
        app.logger.error(e)
    return creds


def perm_add(sheet_id, add_users, service=None):
    """ Used to update permissions. Currently Only add users.
        add_users can be a list of strings, with each string an email address to give reader permissions.
        add_users can be a list of objects, each with a 'emailAddress' key, and an option 'role' key.
        add_users can be a single entity of either of the above.
        This function returns a dictionary that includes all permissions for the provided sheet, & URL for the sheet.
    """
    def callback(request_id, response, exception):
        if exception:
            # TODO: Handle error
            app.logger.error(exception)
        else:
            # app.logger.info(f"Permission Id: {response.get('id')} Request Id: {request_id}")
            pass

    if not service:
        creds = get_creds(service_config['sheets'])
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    batch = service.new_batch_http_request(callback=callback)
    if not isinstance(add_users, list):
        add_users = [add_users]
    for user in add_users:
        if isinstance(user, str):
            user = {'emailAddress': user}
        user_permission = {
            'type': 'user',
            'role': user.get('role', 'reader'),
            'emailAddress': user.get('emailAddress')
        }
        batch.add(service.permissions().create(
                fileId=sheet_id,
                body=user_permission,
                fields='id',
        ))
    batch.execute()
    return perm_list(sheet_id, service=service)


def all_files(*args, service=None):
    """ List, and possibly manage, all files owned by the app """
    app.logger.info(f"======== List all Google Sheet Files ========")
    if not service:
        creds = get_creds(service_config['sheets'])
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    files_list = service.files().list().execute().get('files', [])
    data = []
    for file in files_list:
        id = file.get('id')
        admin_id = current_user.id
        link = f"https://docs.google.com/spreadsheets/d/{id}/edit#gid=0"
        file_type = re.sub('^application/vnd.google-apps.', '', file.get('mimeType'))
        data.append({'id': id, 'admin_id': admin_id, 'name': file.get('name'), 'link': link, 'type': file_type})
    return data


def perm_list(sheet_id, service=None):
    """ For a given worksheet, list who currently has access to view it. """
    if not service:
        creds = get_creds(service_config['sheets'])
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    data = service.files().get(fileId=sheet_id, fields='name, id, permissions').execute()
    data['id'] = data.get('id', data.get('fileId', sheet_id))
    data['link'] = data.get('link', f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid=0")
    return data


def create_sheet(model, service=None):
    """ Takes in a Model instance, usually from Campaign or User (but must have a name property) and create a worksheet. """
    app.logger.info(f'======== create {model.name} sheet ========')
    if not service:
        creds = get_creds(service_config['sheets'])
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    timestamp = int(dt.timestamp(dt.now()))
    name = str(model.name).replace(' ', '_')
    title = f"{name}_{timestamp}"
    spreadsheet = {'properties': {'title': title}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    message = f"Before you can view the Google Sheet, you must give yourself access "
    message += f"with the View and Manage Access link."
    flash(message)
    return update_sheet(model, id=spreadsheet.get('spreadsheetId'), service=service)


# TODO: ? Is this going to be used, or it should be deleted?
def read_sheet_full(id=SHARED_SHEET_ID, service=None):
    """ Get the information (not the values) for a worksheet with permissions granted to our app service. """
    app.logger.info('================== read sheet full =======================')
    if not service:
        creds = get_creds(service_config['sheets'])
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    ranges = ['Sheet1!A1:B3']
    include_grid_data = True  # Ignored if a field mask was set in the request.
    request = service.spreadsheets().get(spreadsheetId=id, ranges=ranges, includeGridData=include_grid_data)
    spreadsheet = request.execute()
    id = spreadsheet.get('spreadsheetId')
    # pprint(spreadsheet)
    link = f"https://docs.google.com/spreadsheets/d/{id}/edit#gid=0"
    return (spreadsheet, id, link)


def read_sheet(id=SHARED_SHEET_ID, range_=None, service=None):
    """ Read a sheet that our app service account has been given permission for. """
    app.logger.info(f'============== read sheet: {id} =====================')
    if not service:
        creds = get_creds(service_config['sheets'])
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    # TODO: Currently okay if range_ is known. Otherwise we need to figure it so we can see the sheet data.
    range_ = range_ or 'Sheet1!A1:B3'
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
    spreadsheet['id'] = spreadsheet.get('spreadsheetId', id)
    spreadsheet['link'] = spreadsheet.get('link', f"https://docs.google.com/spreadsheets/d/{id}/edit#gid=0")
    return spreadsheet


def get_vals(model):
    """ Get the values we want to put into our worksheet report """
    model_name = model.__class__.__name__
    if model_name == 'User':
        # flash(f"Sheet has {model.role} {model_name} data for {model.name}. ")
        insights = model.insight_report()
        media_posts = model.export_posts()
        sheet_rows = [*insights, [''], *media_posts, ['']]
    elif model_name == 'Campaign':
        # flash(f"Sheet has {model_name} data for {model.name}. ")
        brands = ['Brand', ', '.join([ea.name for ea in model.brands])]
        users = ['Influencer', ', '.join([ea.name for ea in model.users])]
        brand_data = [model.brands[0].insight_summary(label_only=True)]
        for brand in model.brands:
            brand_data.append(brand.insight_summary())
        media_posts = model.export_posts()
        sheet_rows = [brands, users, [''], *brand_data, [''], *media_posts, ['']]
        for brand in model.brands:
            sheet_rows.extend(brand.insight_report())
    else:
        logstring = f'Unexpected {model_name} model at this time'
        flash(logstring)
        app.logger.error(f'-------- {logstring} --------')
        data = [logstring]
        media_posts = [['media_posts label row']]
        sheet_rows = [data, [''], *media_posts, ['']]
    return sheet_rows


def compute_A1(arr2d, start='A1', sheet='Sheet1'):
    """ Determine A1 format for 2D-array input, on given sheet, starting at given cell.
        This algorithm assumes that exceeding 26 columns moves into the AA range and beyond.
        It is possible that Google Sheets only allows a max of 26 columns and 4011 rows.
     """
    row_count = len(arr2d)
    col_count = len(max(arr2d, key=len))
    # TODO: write regex that separates the letter and digit sections. 'A1' would have following result:
    col, row = 'A', 1
    col_offset = ord('A') - 1  # 64
    max_col = ord('Z') - col_offset  # 26
    final_col = ''
    num = ord(col) - col_offset + col_count
    while num:
        num, mod = divmod(num, max_col)
        if mod == 0:
            num, mod = num - 1, max_col
        final_col = chr(mod + col_offset) + final_col
    # final_col is the correct string, even if in the AA to ZZ range or beyond
    # TODO: Find out if the max rows is 4011 and max cols is 26. Manage if we exceed the max.
    final_row = row_count + row
    result = f"{sheet}!{start}:{final_col}{final_row}"
    # app.logger.info(f"A1 format is {result} for {row_count} rows & {col_count} columns")
    return result


def update_sheet(model, id=SHARED_SHEET_ID, service=None):
    """ Get the data we want from the model instance, then append it to the worksheet """
    app.logger.info(f'================== update sheet {id} =======================')
    if not service:
        creds = get_creds(service_config['sheets'])
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    value_input_option = 'USER_ENTERED'  # 'RAW' | 'USER_ENTERED' | 'INPUT_VALUE_OPTION_UNSPECIFIED'
    insert_data_option = 'OVERWRITE'  # 'OVERWITE' | 'INSERT_ROWS'
    major_dimension = 'ROWS'  # 'ROWS' | 'COLUMNS'
    vals = get_vals(model)
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
    try:
        spreadsheet = request.execute()
    except Exception as e:
        spreadsheet = {}
        app.logger.error(f"Could not update sheet: {e}")
    return read_sheet(id=spreadsheet.get('spreadsheetId', id), range_=range_, service=service)
