# Feature Development Plan

Key:

- [x] Completed.
- [N] No: does not work or decided against.
- [ ] Still needs to be done.
- [?] Unsure if needed.
- [s] Stretch Goal. Not for current feature plan.

Current Status:
2019-10-30 21:38:05
<!-- Ctrl-Shift-I to generate timestamp -->

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
  - [N] or [try raw](https://docs.simplelogin.io/docs/code-flow/)
  - [N] or research other options
- [x] Confirm FaceBook Login for Influencer users works.
  - [x] Confirm Influencer can login
  - [x] Capture and confirm token
- [x] Get Influencer instagram account (through their pages)
- [ ] DB Design: Track different businesses and how influencers affect each of them?
  - [x] Influencer User Table
  - [x] Brand Table
  - [x] User Model with constructor function for translating from FB.
  - [x] Decide on fields from insights data.
  - [x] Insight to track time series
  - [x] Update ON DELETE for a Users child insights and audience.
  - [s] Post to track different "media" posts.
  - [s] Update ON DELETE for a User's posts.
  - [s] Model for capturing the limited time FB/IG stories
  - [s] Metrics for limited time FB/IG stories
  - [ ] Manage incoming insight duplications
  - [ ] Make sure incoming audience data does not overwrite historical audience data.
  - [ ] Can make a connection between a brand and a user.
    - [ ] Define a campaign for each connection.
- [ ] Add a logical catch for existing users to re-route to data update
  - [ ] For all data collection on new users, move to external functions
  - [ ] Refactor User data collection functions to work on create and update
  - [ ] Refactor User data collection functions to work also work for Brands
- [ ] Can Update data for existing Influencer Users
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
  - [x] Start style design based on Bacchus style guide and website
  - [x] Begin update for our context
  - [ ] Page styling of admin sections to assist in clear reports and navigation
  - [ ] Attractive page styling for Influencer sign up portal & documents (ToS, privacy, etc)
  - [ ] Attractive and clear styling for views seen by Influencers.
- [ ] Can have Brand give permission for the FB App
- [ ] Create Test Users (need a FB page and Instagram business account).
- [ ] Form Validate: Add method to validate form. Ensure other values cannot be injected.
- [ ] Error handling on adding user with duplicate email address.
- [ ] Error handling on adding user with duplicate name.
- [ ] Refactor routes to their own file
- [ ] Add Google Drive API to GCloud app.
- [ ] Add functionality to export Marketing data to a Google worksheet.
  - [ ] create a view for the desired data
  - [ ] refactor view to export to a google worksheet
- [ ] Login: any additional User and Admin authentication needed?
  - [ ] ?Confirm Google login for Worksheet access?
  - [ ] ?Add our own App Auth: User management, adding/updating, auth, password, etc.
  - [ ] Admin: only allow admin to see list and (potential) admin views
