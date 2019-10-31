# social_network

**Author**: Chris L Chapman
**Version**: 0.0.1

## Deployment

Current [Dev Proof-of-Concept Site](https://social-network-255302.appspot.com/)

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

[Features & Tasks](./checklist.md)

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
  - [x] User Model with constructor function for translating from FB.
  - [x] Decide on fields from insights data.
  - [x] Insight to track time series
  - [x] Update ON DELETE for a Users child insights and audience.
  - [?] Post to track different "media" posts.
  - [?] Update ON DELETE for a User's posts.
  - [ ] Manage incoming insight duplications
  - [ ] Make sure incoming audience data does not overwrite historical audience data.
  - [ ] Can make a connection between a brand and a user.
    - [ ] Define a campaign for each connection.
- [ ] Can Update data for existing Influencer Users
- [ ] Add a logical catch for existing users to re-route to data update
- [ ] Refine Brand Model with constructor function for translating from FB.
- [ ] Can update data for existing Brand accounts
- [ ] Refine decision for fields from insights data.
- [x] CRUD methods updated for all models.
- [x] Get appropriate data from FaceBook's Graph API stored to the DB.
  - [x] User profile info
  - [x] User Business Instagram Account
  - [x] Insights data
  - [x] Useful network data
- [x] Can add new Influencer Users (first must be added as Test Users)
- [x] Graph showing all Insight data for a given user.
- [x] Data sent to graph template setup to allow a variety of different view options.
- [x] Insight Graph with javascript buttons to toggle which data shows.
- [ ] Styling & Presentation
  - [ ] Page styling of admin sections to assist in clear reports and navigation
  - [ ] Attractive page styling for Influencer sign up portal & documents (ToS, privacy, etc)
  - [ ] Attractive and clear styling for views seen by Influencers.
- [ ] Can have Brand give permission for the FB App
- [ ] Create Test Users (need a FB page and Instagram business account).
- [ ] Form Validate: Add method to validate form. Ensure other values cannot be injected.
- [ ] Error handling on adding user with duplicate email address.
- [ ] Error handling on adding user with duplicate name.
- [ ] ?Refactor routes to their own file?
- [ ] Add Google Drive API to GCloud app.
- [ ] Add functionality to export Marketing data to a Google worksheet.
  - [ ] create a view for the desired data
  - [ ] refactor view to export to a google worksheet
- [ ] Login: any additional User and Admin authentication needed?
  - [ ] ?Confirm Google login for Worksheet access?
  - [ ] ?Add our own App Auth: User management, adding/updating, auth, password, etc.
  - [ ] Admin: only allow admin to see list and (potential) admin views

## User Stories

### Influencer - bringing social value

- As an active market influencer for a few years, they have seen growth in social following, and social mentions in the market, which are of great value. However, they are interested and unsure of what clearly defined value this brings their company in sales, conversion or loyalty.
- As a market influencer engaged with a brand, they would like to see the ongoing impact of their campaign efforts has on their audience, the partner brand, and on their own personal branding. This can assist them in fine-tuning and delivering their desired message.
- As an active market influencer beginning new brand relationships, they would like to provide usable and verifiable data on the value they bring to their brand partners.
- As a market influencer, they would like their significant history of influence and reach to be recognized by brands and marketing team members.
- App use: Can easily login with facebook credentials and grant permission to our app
- App use: Can review the permissions and revoke them at any time.
- App use: Can setup the parameters for a campaign (or is this marketing team task?)

### Brand - Deciding where to invest

- As a brand company active with market influencers for a a few years, they are satisfied that their influencer activity brings significant value to their brand. However, they feel their influencer strategy could be optimized, especially as the market becomes more crowded and competitive. The brand company wants to know how to leverage influencer campaigns in their overall marketing strategy, by amplifying and tracking gained users.
- As a brand company that has been active in influencer marketing for a few years, they are concerned with the rising prices for both influencer campaigns and for social paid ads. The brand company wants to invest their budget where the most impact can be gained. However, they do not have the data on either to understand and determine their best options.
- A given brand company has resisted influencer marketing for a decade, but has previously benefited from organic reach. They are seeking advice on how to use other channels - earned and paid - so they do not lose market share.
- As a brand company without a strong social marketing history, they are cautiously new to paid social and they are skeptical about influencer marketing. They want to invest in both, but need measurable systems with clearly defined data to justify investment in this typically fuzzily defined field driven by vanity metrics.

### Marketing - Manager of the Campaign

- As a marketer who has been active with social influencers for a few years, they have historically seeded/sampled/gifted product or paid for product placement in an influencer feed. They are unsure the actual ROI and is looking to understand which influencers bring the most real quality audience/customers.
- As a marketer who is relatively new to influencer marketing, they answer to senior leadership who want clearly defined measurable results. This influencer marketing campaign must be comparable with all their other marketing opportunities, with all projects ladder up to a 360* digital eco-system. Without enough data on influencer campaigns, the marketing team cannot justify investment compared to their other clearly defined digital strategies.
- App use: Can view useful and clearly defined data using google worksheets
- App use: They know they are viewing reliable and accurate data.
- App use: Does not need to issue commands or modify the code for the data they want
