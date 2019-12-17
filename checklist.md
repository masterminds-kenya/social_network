# Feature Development Plan

## Milestones

| Complete           | Task                                      |
| ------------------ |:-----------------------------------------:|
|                    | **Start of Project**                      |
| :heavy_check_mark: | Requirements gathering and begin project  |
|                    | **Milestone 1 Completion**                |
| :heavy_check_mark: | Servers set up                            |
| :heavy_check_mark: | Database connected                        |
| :heavy_check_mark: | Influencer or Brand can give permissions to account data|
|                    | **Milestone 2 Completion**           |
| :heavy_check_mark: | Influencer/Brand can select which Instagram account to use|
| :heavy_check_mark: | Facebook API data is collected & stored to database |
| :heavy_check_mark: | Google Sheets connected to Facebook API database    |
| :heavy_check_mark: | Getting Media Posts (non-Story) metrics captured & stored |
| :heavy_check_mark: | Getting Story Posts metrics captured & stored  |
| :heavy_check_mark: | Campaign create & edit - can connect Users & Brands |
| :heavy_check_mark: | Posts can be assigned as in or out of campaign |
|                    | **Milestone 3 Completion**           |
| :heavy_check_mark: | Generate reports to Google sheets    |
| :heavy_check_mark: | Give permissions to view google sheets      |
|                    | Hosting and Facebook settings on Bacchus accounts |
|                    | **Milestone 4 Completion**           |
|                    | Site content and style, basic UI and graphs |
|                    | Testing, on-boarding, error handling |
|                    | Facebook App approved and go live    |
|                    | **Initial Contract Completion**      |

## Checklist

### Key

- [x] Completed.
- [N] No: does not work or decided against.
- [ ] Still needs to be done.
- [?] Unsure if needed.
- [s] Stretch Goal. Not for current feature plan.

Current Status:
2019-12-10 16:32:41
<!-- Ctrl-Shift-I to generate timestamp -->

### DB Design: Track different businesses and how influencers affect them

- [x] Influencer User Table
- [x] Brand Table
- [x] User Model with constructor function for translating from FB.
- [x] Decide on fields from insights data.
- [x] Insight to track time series
- [x] Update ON DELETE for a Users child insights and audience.
- [s] Post to track different "media" posts.
- [s] Update ON DELETE for a User's posts.
- [s] Model for capturing the limited time FB/IG stories
- [x] Fix DB setup: use utf8mb4 so we can handle emojis
- [x] posts (media) seem to have 3 types: Story, Album, and Photo/Video
  - [x]  All IG Media also has some general returnable fields:
    - [x]  caption  - except emoji problem
    - [x]  comments_count
    - [x]  like_count
    - [x]  media_type
    - [x]  permalink
  - [x] Stories Insight Metrics (for limited time FB/IG stories)
    - [x] exits
    - [x] impressions
    - [x] reach
    - [?] replies
    - [x] taps_forward
    - [x] taps_back
  - [x] Photo/Video Insight Metrics
    - [x] engagement
    - [x] impressions
    - [x] reach
    - [x] saved
    - [x] video_views
  - [x] Album Insight Metrics
    - [x] Probably need to regex to fix the key for the Model.
    - [x] carousel_album_engagement
    - [x] carousel_album_impressions
    - [x] carousel_album_reach
    - [x] carousel_album_saved
    - [N] carousel_album_video_views
- [x] Refactor User Model, less PII, no admin, connect to posts/media
- [x] Have the ability for a single FB user to have many IG profiles on our app?
- [x] User Model creation works if new Influencer has multiple IG accounts.
- [x] ?DB create handles update if record already exists?
  - [?] Corrects for double click on starting any API fetch and save process
  - [x] Corrects for overlapping results from a previous batch of posts requests
  - [x] Corrects for overlapping results from a previous batch of insights requests
  - [x] Corrects for overlapping results from a previous batch of audiences requests
- [s] Manage incoming insight duplications
- [s] How do we want to organize audience data?
- [s] Refactor Audience Model to parse out the gender and age group fields
- [s] After refactor, make sure audience data does not overwrite previous data
- [x] Campaign Model
  - [s] Can make a connection between a brand and a user.
  - [s] Can create a campaign for each connection.
  - [x] Allow admin to categorize posts to campaigns
  - [x] Allow admin to indicate a post has been processed even if not assigned.
- [x] For all data collection on new users, move to external functions
- [s] Refactor User data collection functions to work also work for Brands
- [x] Create many function
- [x] Refactor create function to account for both create one or create many
- [s] Update many function
- [s] Refine Brand Model with constructor function for translating from FB.
- [s] Can update data for existing Brand accounts
- [ ] Update User & Brand to be the same user table
  - [ ] Default account insights history, 360 days.
  - [x] Export Influencer/Brand metrics to google worksheet.
- [ ] Pickle tokens
- [n] Keep a DB table of worksheet ids?
  - [s] Will we have multiple report views?
- [s] DB Migration: Integrate flask-migrate?
- [ ] Revisit method of reporting Campaign Results.
- [ ] Revisit structure for ON DELETE, ON UPDATE,
- [ ] Revisit structure for how related tables are loaded (lazy=?)
- [?] Refine decision for fields from (overall user) insights data.

### Site Functionality

- [x] Add Brand account metrics to the Campaign report
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
- [x] User creation: Manage if influencer has many IG accounts.
- [s] Can have Brand give permission for the FB App
- [x] Admin can input information for a brand
- [x] API call and store basic metrics for media Posts
- [x] API call and store post insight metrics for Photo/Video
- [x] API call and store post insight metrics for Albums
- [x] API call and store post insight metrics for Stories
- [s] WebHook to get Stories data at completion.
- [ ] Decide approach: A) typical form validation & stop submission of existing or B) use existing record.
  - [ ] If form validate approach, setup user experience that they can select existing record
  - [ ] If incoming form (or API user/brand) already exists, use existing instead of create new:
    - [x] Catch and handle attempt to create a duplicate existing User account
    - [ ] Catch and handle if a User account is trying to add an IG account already used by (another) User account
    - [ ] Catch and handle if trying to create an already existing Campaign name
    - [x] Catch and handle attempt to create a duplicate existing Brand account
- [ ] Allow a Brand to give permissions for FB and IG.
  - [ ] If Brand name already in system, associate with that existing record
  - [ ] exactly how this works depends on approach A or B for how to handle validation w/ existing records
- [x] Refactor User data collection functions to work on create and update
- [x] Can issue new API requests for recent data for existing Influencer Users
- [x] Admin/Marketing can connect Influencer to Brands through Campaign
- [x] Create Brand and Campaign View
  - [x] Create Brand
  - [x] Create Campaign
  - [x] Assign Users to Campaign
- [ ] User detail view reports current number of posts we have stored
- [ ] For User Model: add followers_count, follows_count, media_count
- [x] Post Detail view
  - [x] Only show the appropriate fields the media_type
    - [x] Before rendering template, limit object to only have appropriate fields.
  - [s] Sort or Filter to show posts by processed or not yet processed
  - [s] Sort or Filter to show posts that are assigned to a campaign
  - [s] Sort or Filter to show posts that were rejected from being in a campaign
- [x] Campaign Manage View
  - [x] List all Influencers in this campaign
  - [x] For each Influencer, list media to process.
    - [x] able to filter for only unprocessed posts.
    - [x] fetch new posts to add to be processed
      - [x] ?Change what view it shows when completed?
    - [x] radio button to confirm post is part of campaign
    - [x] radio button to confirm post is NOT part of campaign
    - [x] can skip processing a seen post, to categorize it later
    - [x] Can navigate to Detail View to see posts assigned to campaign
    - [x] Campaign form elements nicely on the side of post details
    - [x] Can view already assigned posts and reprocess them - see Campaign Detail
- [s] ?Influencer can create a Campaign to connect to Brand?
- [x] Campaign Collection - Detail View w/ assigned posts
  - [ ] ?Decide if it should show more metrics or results?
  - [ ] ?Update link text from Management page, currently says "Campaign Results"?
  - [x] can view all posts currently assigned to this campaign
  - [x] can navigate to Campaign Manage view to add posts to campaign
  - [x] Can remove from campaign & back in cue to decide later (marked unprocessed)
  - [x] Can remove to campaign and remove for consideration (marked processed)
  - [x] Will be left with current settings if unchanged when other posts modified
- [ ] Campaign Results View
  - [x] Overview of the campaign metrics
- [x] Functionality to Fetch more posts (API call to FB)
  - [x] Can request more posts for a given user
  - [x] redirect back to the page/view that called to get more posts
  - [s] Will limit request to only get new posts since last request
  - [x] In case we do get duplicates, it will NOT create duplicates in DB
    - [x] Will update if our DB info is out-of-date
  - [ ] Visual feedback that it is processing but not ready to render new view
- [ ] Fetch more Insights (of the account, not of media)
  - [x] Can get a history the the user (or brand) account insights
  - [ ] Will limit request to only get new insights since last request
  - [ ] In case we do get duplicates, it will NOT create duplicates in DB
      - [ ] Will update if our DB info is out-of-date
- [x] Add Google Sheet API to GCloud app.
- [x] Add Google Drive API to GCloud app.
- [x] Add functionality to export Marketing data to a Google worksheet.
  - [x] App can navigate credentials to allow full Google Sheet API features.
  - [x] Resolve: if sheet owned by App, can marketing modify or use it?
    - [x] Give permission to other users to view an app owned spreadsheet
    - [x] Able to read and edit a worksheet created elsewhere & hard-coded in
    - [s] Embed the worksheet as a view in our app (after admin login feature)
    - [n] Do we need to have marketing user own the worksheet and App allowed to edit?
  - [x] Function to create a worksheet
  - [x] Function to update a worksheet
  - [x] Can read and format desired DB data into worksheet.
- [x] create a route & view for the sheets data view
- [ ] For a given worksheet, ability to edit existing permissions
- [ ] For a given worksheet, ability to delete existing permissions
- [ ] For a given worksheet, ability to delete the file
- [ ] More Drive files management
  - [ ] List all files
  - [ ] Manage those files
- [ ] Attach worksheets to the Campaign model so we not always creating new.
- [s] Add migration functionality?
- [ ] Move hosting and FaceBook settings to Bacchus
- [x] refactor sheets data view to export to a google worksheet
- [ ] Login: any additional User and Admin authentication needed?
  - [ ] ?Confirm Google login for Worksheet access?
  - [ ] ?Add our own App Auth: User management, adding/updating, auth, password, etc.
  - [ ] Admin: only allow admin to see list and (potential) admin views

### Site Content & Style

- [x] Start style design based on Bacchus style guide and website
- [x] Begin update for our context
- [ ] Page styling of admin sections to assist in clear reports and navigation
- [ ] Attractive page styling for Influencer sign up portal & documents (ToS, privacy, etc)
- [ ] Content for Influencer sign-up portal (home view) to give them confidence in the process.
- [ ] Content for Privacy page
- [ ] Content for Tos page
- [ ] Attractive and clear styling for profile and data views seen by Influencers.

### Code Structure, Testing, Clean up

- [x] Setup a real influencer (Noelle Reno) as a confirmed tester.
- [x] Have real influencer (Noelle Reno) sign up for testing.
- [x] Modularize the codebase: sheets, facebook api, developer_admin, manage
- [ ] Update template to use for-else: in jinja, the else only runs if no iteration
- [x] Modularize the codebase more: move routes elsewhere?
- [x] ? allow logging in related files (remove all print statements) == from flask import current_app as app
- [ ] Update forms and API digesting with input validation to replace following functionality:
  - [ ] Currently fix_date used for both create model, and when create_or_update many
  - [ ] Currently create_or_update_many also has to modify inputs from Audience API calls
  - [ ] Should campaign management view extend base instead of view?
  - [ ] Is current onboard process slow? Delay some data collection?
  - [ ] Other feedback for expected sign up flow?
  - [ ] Review data options to confirm our desired data collection.
- [ ] Create Test Users (need a FB page and Instagram business account).
- [ ] Test influencer flow after completion (Have Noelle go through process again)
- [ ] Regex for A1 notation starting cell.
- [x] Code Refactor: move routes to their own files
- [x] Code Refactor: more modular code structure
- [ ] Revisit Code Refactor: even more modular code structure?
- [ ] Form Validate: Add method to validate form. Safe against form injection?
- [ ] Error handling on adding user with duplicate email address.
- [ ] Error handling on adding user with duplicate name.
