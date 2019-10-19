# social_network

**Author**: Chris L Chapman
**Version**: 0.0.1

## Deployment

We are currently deploying on google cloud (gcloud), with a flask server. Gcloud is expecting a pip requirements file (requirements.txt), an app.yaml file (indicating what python version to use), and a main.py file for our server code file. Gcloud also allows an ignore file (.gcloudignore) which follows the same concepts from .gitignore files. Locally we are using pipenv to help us track dependencies and packages only needed in the development environment. However, the Pipfile and Pipfile.lock files should be in the ignore file for uploading to gcloud.

## Development notes

We are expecting an `.env` file at the root of the project so the `config.py` works correctly. For deployment, we also need to update the `app.yaml` file with the appropriate environment variables.

When running locally, we can proxy the database. This requires a cloud_sql_proxy file, and knowing the DB_CONNECTION_NAME. In the terminal, substituting as needed, execute the following command:

``` bash
./cloud_sql_proxy -instances="DB_CONNECTION_NAME"=tcp:3306
```

We can create the database tables by running:

``` bash
python application/model_db.py
```

### TODO

- [x] Confirm DB connection works
- [x] CREATE: Confirm we can add users to DB
- [x] READ:   Confirm we can retrieve user info from DB.
- [x] UPDATE: update user in DB.
- [x] DELETE: remove user from DB.
- [x] LIST: Admin list view (initially insecure route)
- [x] Redirect existing FB app settings to current project.
- [N] For development, try using [ngrok](https://ngrok.com/)
- [x] Decide FaceBook Login Implementation.
  - [N] NO: try python facebook-sdk
  - [x] try implementing with requests_oauthlib
  - [n] or [try raw](https://docs.simplelogin.io/docs/code-flow/)
  - [n] or research other options
- [x] Confirm FaceBook Login for Influencer users works.
  - [x] Confirm Influencer can login
  - [x] Capture and confirm token
- [x] Get Influencer instagram account (through their pages)
- [ ] DB Design: Track different businesses and how users affect each of them?
  - [x] Influencer User Table
  - [x] Brand Table
  - [ ] Assume Many-to-Many, decide on fields from insights data.
  - [?] Insight to track time series
  - [?] Post to track different "media" posts.
  - [ ] Update ON DELETE for the child insights and posts.
- [x] CRUD methods updated for all models.
- [ ] Get appropriate data from FaceBook's Graph API stored to the DB.
  - [x] User profile info
  - [x] User Business Instagram Account
  - [x] Insights data
  - [x] Useful network data
- [x] Can add new Influencer Users (currently must be added as Test Users)
- [ ] Can Update data for existing Influencer Users
- [ ] Add a logical catch for existing users to re-route to data update
- [ ] Can have Brand give permission for the FB App
- [ ] Can update data for existing Brand accounts
- [ ] Create Test Users (need a FB page and Instagram business account).
- [ ] Login: any additional User and Admin authentication needed?
  - [ ] ?Confirm Google login for Worksheet access?
  - [ ] ?Add our own App Auth: User management, adding/updating, auth, password, etc.
- [ ] Admin: only allow admin to see list and (potential) admin views
- [ ] User (and Brand?) Constructor function for translating from FB.
- [ ] Form Validate: Add method to validate form. Ensure other values cannot be injected.
- [ ] Error handling on adding user with duplicate email address.
- [ ] Error handling on adding user with duplicate name.
- [ ] ?Refactor routes to their own file?
- [ ] Add Google Drive API to GCloud app.
- [ ] Add functionality to export Marketing data to a worksheet.
  - [ ] create a view for the desired data
  - [ ] refactor view to export to a google worksheet

## User Stories

### Influencer

- Can easily login with facebook credentials and grant permission to our app
- Can review the permissions and revoke them at any time.

### Marketing

- Can view data using google worksheets
- Does not need to issue commands or modify the code for the data they want
