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
|                    | Influencer/Brand can select which Instagram account to use|
| :heavy_check_mark: | Facebook API data is collected & stored to database |
| :heavy_check_mark: | Google Sheets connected to Facebook API database    |
| :heavy_check_mark: | Getting Media Posts (non-Story) metrics captured & stored |
|  needs testing     | Getting Story Posts metrics captured & stored  |
| :heavy_check_mark: | Campaign create & edit - can connect Users & Brands |
|                    | Posts can be assigned as in or out of campaign |
|                    | **Milestone 3 Completion**           |
|                    | Generate reports to Google sheets    |
|                    | Give permissions to view google sheets      |
|                    | Site content and style, basic UI and graphs |
|                    | Testing, on-boarding, error handling |
|                    | **Milestone 4 Completion**           |
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
2019-10-30 21:38:05
2019-11-05 09:42:07
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
- [ ] posts (media) seem to have 3 types: Story, Album, and Photo/Video
  - [x]  All IG Media also has some general returnable fields:
    - [x]  caption  - except emoji problem
    - [x]  comments_count
    - [x]  like_count
    - [x]  media_type
    - [x]  permalink
  - [ ] Stories Insight Metrics (for limited time FB/IG stories)
    - [ ] exits
    - [ ] impressions
    - [ ] reach
    - [ ] replies
    - [ ] taps_forward
    - [ ] taps_back
  - [x] Photo/Video Insight Metrics
    - [x] engagement
    - [x] impressions
    - [x] reach
    - [x] saved
    - [x] video_views
  - [x] Album Insight Metrics
    - [x] carousel_album_engagement
    - [x] carousel_album_impressions
    - [x] carousel_album_reach
    - [x] carousel_album_saved
    - [N] carousel_album_video_views
- [x] Refactor User Model, less PII, no admin, connect to posts/media
- [x] Have the ability for a single FB user to have many IG profiles on our app?
- [ ] User Model creation works if new Influencer has multiple IG accounts.
- [s] Manage incoming insight duplications
- [s] How do we want to organize audience data?
- [s] Refactor Audience Model to parse out the gender and age group fields
- [s] After refactor, make sure audience data does not overwrite previous data
- [ ] Campaign Model
  - [s] Can make a connection between a brand and a user.
  - [s] Can create a campaign for each connection.
  - [ ] Allow admin to categorize posts to campaigns
  - [ ] Allow admin to indicate a post has been processed even if not assigned.
- [x] For all data collection on new users, move to external functions
- [s] Refactor User data collection functions to work also work for Brands
- [x] Create many function
- [ ] Refactor create to account for both create one or create many
- [s] Update many function
- [s] Refine Brand Model with constructor function for translating from FB.
- [s] Can update data for existing Brand accounts
- [ ] Keep a DB table of worksheet ids?
  - [ ] Will we have multiple report views?
- [s] DB Migration: Integrate flask-migrate?
- [ ] Revisit structure for ON DELETE, ON UPDATE,
- [ ] Revisit structure for how related tables are loaded (lazy=?)
- [?] Refine decision for fields from (overall user) insights data.

### Site Functionality

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
- [ ] User creation: Manage if influencer has many IG accounts.
- [s] Can have Brand give permission for the FB App
- [x] Admin can input information for a brand
- [x] API call and store basic metrics for media Posts
- [x] API call and store post insight metrics for Photo/Video
- [ ] API call and store post insight metrics for Albums
- [ ] API call and store post insight metrics for Stories
- [s] WebHook to get Stories data at completion.
- [ ] Add a logical catch for existing users to re-route to data update
- [x] Refactor User data collection functions to work on create and update
- [x] Can issue new API requests for recent data for existing Influencer Users
- [x] Admin/Marketing can connect Influencer to Brands through Campaign
- [x] Create Brand and Campaign View
  - [x] Create Brand
  - [x] Create Campaign
  - [x] Assign Users to Campaign
- [ ] Campaign Detail & Manage View
  - [ ] List all Influencers in this campaign
  - [ ] For each Influencer, list media to process.
    - [ ] maintain a cue of unprocessed posts.
    - [ ] fetch new posts to add to the cue
    - [ ] checkbox to confirm post is part of campaign
    - [ ] checkbox to confirm post is NOT part of campaign
- [?] ?Influencer can create a Campaign to connect to Brand?
- [x] Add Google Sheet API to GCloud app.
- [ ] Add functionality to export Marketing data to a Google worksheet.
  - [x] App can navigate credentials to allow full Google Sheet API features.
  - [ ] Resolve: if sheet owned by App, can marketing modify or use it?
    - [ ] Give permission to other users to view an app owned spreadsheet
    - [x] Able to read and edit a worksheet created elsewhere, and permissions given to our app.
    - [ ] Embed the worksheet as a view in our app, if user is authorized (req add login)
    - [ ] Do we need to have marketing user own the worksheet and App allowed to edit?
  - [x] Function to create a worksheet
  - [x] Function to update a worksheet
  - [ ] Can read and format desired DB data into worksheet.
- [x] create a route & view for the sheets data view
- [ ] refactor sheets data view to export to a google worksheet
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
  - [ ] Is current process slow? Move some data collection outside of sign up flow?
  - [ ] Other feedback for expected sign up flow?
  - [ ] Review data options to confirm our desired data collection.
- [ ] Create Test Users (need a FB page and Instagram business account).
- [ ] Test influencer flow after completion (Have Noelle go through process again)
- [ ] Regex for A1 notation starting cell.
- [ ] Code Refactor: move routes to their own files
- [ ] Code Refactor: more modular code structure
- [ ] Form Validate: Add method to validate form. Ensure other values cannot be injected.
- [ ] Error handling on adding user with duplicate email address.
- [ ] Error handling on adding user with duplicate name.
