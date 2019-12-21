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
| :heavy_check_mark: | Hosting and Facebook settings on Bacchus accounts |
|                    | **Milestone 4 Completion**           |
|                    | Admin & Manager Pages require login |
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
2019-12-19 21:47:30
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
- [x] posts (media) seem to have 4 types: Story, Album, Photo, and Video
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
- [x] Update User & Brand to be the same user table
- [x] Refactor to single User Model for all types: influencer, brand, manager, admin
- [x] Add Insight metric 'online_followers'
- [x] Insight metrics for IG profile interactions.
- [x] Business Discovery data: followers_count, media_count. Others are more account info.
- [x] Default account insights history, 360 days.
- [x] Campaign worksheet exports summary of Brand account metrics (if IG account was associated)
- [ ] Pickle tokens
- [n] Keep a DB table of worksheet ids?
  - [s] Will we have multiple report views?
- [s] DB Migration: Integrate flask-migrate?
- [ ] Revisit method of reporting Campaign Results.
- [ ] Revisit structure for ON DELETE, ON UPDATE,
- [ ] Revisit structure for how related tables are loaded (lazy=?)
- [x] Refine decision for fields from (overall user) insights data.

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
- [?] Decide approach: A) typical form validation & stop submission of existing or B) use existing record.
  - [n] If form validate approach, setup user experience that they can select existing record
  - [x] If incoming form (or API user/brand) already exists, use existing instead of create new:
    - [x] Catch and handle attempt to create a duplicate existing User account
    - [ ] Catch and handle if a User account is trying to add an IG account already used by (another) User account
    - [ ] Catch and handle if trying to create an already existing Campaign name
    - [x] Catch and handle attempt to create a duplicate existing Brand account
- [x] Allow a Brand to give permissions for FB and IG.
  - [x] If Brand name already in system, associate with that existing record
  - [x] exactly how this works depends on approach A or B for how to handle validation w/ existing records
- [x] Refactor User data collection functions to work on create and update
- [x] Can issue new API requests for recent data for existing Influencer Users
- [x] Admin/Marketing can connect Influencer to Brands through Campaign
- [x] Create Brand and Campaign View
  - [x] Create Brand
  - [x] Create Campaign
  - [x] Assign Users to Campaign
- [s] User detail view reports current number of posts we have stored
- [x] For User, the InstaGram followers_count, media_count are stored as an Audience record.
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
  - [ ] ?Decide if it should show more or fewer metrics or results?
  - [x] ?Update link text from Management page, currently says "Campaign Results"?
  - [x] can view all posts currently assigned to this campaign
  - [x] can navigate to Campaign Manage view to add posts to campaign
  - [x] Can remove from campaign & back in cue to decide later (marked unprocessed)
  - [x] Can remove to campaign and remove for consideration (marked processed)
  - [x] Will be left with current settings if unchanged when other posts modified
- [ ] Campaign Results View
  - [ ] ?Decide if it should show less graphs, or go straight to sheet export.
  - [x] Overview of the campaign metrics
- [x] Functionality to Fetch more posts (API call to FB)
  - [x] Can request more posts for a given user
  - [x] redirect back to the page/view that called to get more posts
  - [s] Will limit request to only get new posts since last request
  - [x] In case we do get duplicates, it will NOT create duplicates in DB
    - [x] Will update if our DB info is out-of-date
  - [ ] Visual feedback that it is processing but not ready to render new view
  - [x] Calling for more Audience data should also call for update on ig_data metrics.
- [ ] Fetch more Insights (of the account, not of media)
  - [x] Can get a history the the user (or brand) account insights
  - [x] Metrics for 'online_followers' automatically updates with Insight updates.
  - [ ] Will limit request to only get new insights since last request
  - [x] In case we do get duplicates, it will NOT create duplicates in DB
    - [x] Will update if our DB info is out-of-date
- [ ] Flash messages for any processes that do not have an obvious update.
  - [ ] Get new posts
  - [ ] get new insights
  - [ ] get new audiences
- [x] Remove link to get Online Followers Report since it is also called by get insights.
- [ ] Ability to update IG account followers_count and media_count stored in Audience
- [ ] Get new Audience data should also call to get the IG account info (followers_count & media_count).
- [x] Move/Relabel/remove 'Admin - Log' link on user detail view.
- [s] Add migration functionality?
- [x] Move hosting and FaceBook settings to Bacchus
- [ ] Research Google Cloud settings to remove delay for website to spin up after idle.

#### Google Drive & Sheets Functionality

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
  - [x] Includes a report for the brand insight metrics on the campaign report
  - [x] Fix computation of A1 formatting when columns go into the double letter range (AA to ZZ)
  - [x] Test & Fix A1 format computation if exceeding the double letter range (after ZZ)
  - [ ] Check if Google Sheets has a max of 26 columns and 4011 rows.
  - [x] From User detail view, can export influencer/brand account metrics to google sheet.
    - [x] This report also includes all posts we have recorded.
  - [ ] Export Sheet functions should use multiple worksheets/tabs in the same file.
- [x] create a route & view for the sheets data view
- [x] For a given worksheet, ability to edit existing permissions
- [ ] For a given worksheet, ability to delete existing permissions
- [ ] For a given worksheet, ability to delete the file
- [ ] More Drive files management
  - [ ] List all files
  - [ ] Manage those files
- [s] Attach worksheets to the Campaign model so we not always creating new.
- [x] refactor sheets data view to export to a google worksheet

#### Login & Authentication Features

- [x] User model has email and password fields, but are not required for Influencers & Brands
- [ ] Can manually create a new User (requires email and password)
- [ ] Can track who the 'current_user' is as they navigate around
- [ ] User created with Facebook login/permissions is integrated with other User methods
- [ ] Login page: During Testing & Approval, show Test Login Details.
- [ ] Allow anonymous user to start the creation of a manager or admin account
  - [ ] New manually created 'manager' or 'admin' users requre Admin approval
- [ ] Allow admin to create a user w/o a password,
  - [ ] Require the user to set password on first login.
- [ ] When Export Sheet is created (for Campaign or User), current_user gets sheet permissions
- [s] When Export Sheet is created, access is granted to some universal Admin
- [ ] ?Confirm Google login for Worksheet access?
- [ ] Auth management features:
  - [ ] Change password
  - [ ] Recover account (via email)
- [ ] Any missed Routes or Template links that should be modified?
- [ ] Other Security checks?

Permissions to Routes and Showing/Hiding links in Templates:

- [ ] Sign Up page requires Influencers and Brands to use FB link
- [ ] Login page encourages Influencers and Brands to use FB link
- [ ] ? Confirm same link, or Update link, for FB signup vs Login.
- [ ] ] List All Influencers
  - [ ] Everyone can see the link, but route requires login.
  - [ ] Can Influencers see list of all Influencers?
  - [ ] Can Brands see list of all Influencers?
- [ ] ] List All Brands
  - [ ] Everyone can see the link, but route requires login.
  - [ ] Can Influencers see list of all Brands?
  - [ ] Can Brands see list of all Brands?
- [ ] View Influencer detail view only for Admin, Manager, and current_user's own profile?
- [ ] View Brand details: Can Influencers see Brands? Can Brands see other Brands?
- [ ] View Influencer details: Can Brands see Influencers? Can other Influencers?
- [ ] On Brand|User lists: Template links to detail views matches permissions to routes.
- [ ] List All Campaigns
  - [ ] route requires authenticated (logged in)
  - [ ] ? Only show link if authenticated, or have consistent UI with User list links?
  - [ ] ? For Influencers: Is list filtered to only ones they are in, or see full list?
  - [ ] ? For Brands: Is list filtered to only ones they are in, or see full list?
- [ ] Signup, Login, Logout
  - [ ] Links to Signup and Login if not authenticated, Logout link if authenticated
  - [ ] Allow special "Signup other User" for manager|admin to create manager|admin|brand user?
- [ ] View your own profile: For authenticated, base shows link to their own detail view.
- [ ] List All Managers Route
- [ ] Base has link to List all Managers for Admin|Manager? Or just Admin? Or never?
  - [ ] Manager and Admin may want to see this to contact or know managers?
  - [ ] Admin may need this for interface to remove managers.
- [ ] Base has link to List all Admins for Admin|Manager? Or just Admin? Or never?
  - [ ] Manager and Admin may want to see and contact|know admin?
  - [ ] Admin may need this for interface to remove admin?
- [ ] Add, Edit, Delete, & View any Model detail route requires authenticated user.
- [ ] Edit and Delete User routes require matching current_user or Admin|Manager
- [ ] User detail view: show Edit & Delete links only if current_user or Admin|Manager
- [ ] Collect (from API call) new Insights | Audiences | Posts for a User
  - [ ] Allow Manager|Admin to do all
  - [ ] Allow Users to only do their own
  - [ ] Only show links if current_user (if allowed) or Manager|Admin
- [ ] Routes/views to see User Insights Summary
  - [ ] Routes only if current_user or Admin|Manager
  - [ ] ? Allow Routes for Brands to see Influencers ?
  - [ ] ? Allow Routes for Influencers to see Brands ?
  - [ ] Links from User detail view to Insight Summary matching permissions to view them.
- [ ] Route to see detail view for Insight only for Admin
  - [ ] The only place for this link would be a special Admin only page.
- [ ] Route to see detail view for Audience only for current_user|Admin|Manager
  - [ ] Link from User detail view to Audience detail view matches permissions to route.
- [ ] Route to see detail view for Post - allowed for all (they are public by IG)
  - [ ] Link to view Post detail view is unmodified wherever shown (public IG post)
- [ ] Route to see anything to do with Google Sheets only for Admin|Manager
  - [ ] Or allow User (influencer or brand) to export their own data?
  - [ ] Or allow Influencer to export Campaigns they are associated with?
  - [ ] Or allow Brand to export Campaigns they are associated with?
- [ ] Add or Edit Campaign routes require Admin|Manager
- [ ] Campaign List view shows link to Add Campaign only if Admin|Manager
- [ ] Campaign List view shows link to Campaign matching who has permissions to route
- [ ] View Campaign Detail (Manage) route require Admin|Manager
  - [ ] ?Allow Campaign Detail route if Influencer is associated to it?
  - [ ] ?Allow Campaign Detail route if Brand is associated to it?
- [ ] Campaign Collected route require Admin|Manager
  - [ ] ?Allow Campaign Collected route if Influencer is associated to it?
  - [ ] ?Allow Campaign Collected route if Brand is associated to it?
- [ ] Campaign Manage|Collected links in Campaign header are unchanged (all here can see link)
- [ ] ?Campaign Results links in Campaign header unchanged (all here can see the link)?
- [ ] ?Campaign Results link in Campaign header matches who has permissions to route?
- [ ] Campaign Results route require Admin|Manager
  - [ ] ?Allow Campaign Results route if Influencer is associated to it?
  - [ ] ?Allow Campaign Results route if Brand is associated to it?
- [ ] Campaign Manage|Collected|Result view shows link to Edit Campaign only if Admin|Manager.
- [ ] Ability to POST to Campaign Manage|Collected (media assignment) only Admin|Manager
- [ ] Show Form element or Button on Campaign Manage|Collected views only Admin|Manager
- [ ] Link to collect more media/posts on any Campaign view unmodified (all here are allowed)
- [ ] Delete Campaign route limited to just Admin or for Admin|Manager?
  - [ ] What if a manager accidentally created one?
- [ ] Link to Delete Campaign from Campaign settings matches permissions to route.
- [ ] On Campaign Results: Link/Form to Export Sheet only shown to Admin|Manage
  - [ ] ? Allow associated Brand to Export Sheet ?
  - [ ] ? Allow associated User to Export Sheet ?
- [ ] ?If Influencer or Brand can see Campaign Results, they do not see Export Sheet option?
- [ ] Admin has an extra view with links that only an Admin needs and is allowed to use.
  - [ ] List all Insights | Audiences | Posts | Managers | Admin
  - [ ] List all Sheets owned by the platform
  - [ ] Manage settings to any specific sheet
    - [ ] Change access
    - [ ] Delete Sheet
  - [s] Global revoke permissions to all Sheet/file in Drive for a given user

### Site Content & Style

- [x] Start style design based on Bacchus style guide and website
- [x] Begin update for our context
- [x] Privacy and tos pages.
- [x] Update all 'user' references to 'influencer' as appropriate
- [ ] Page styling of admin sections to assist in clear reports and navigation
- [ ] Attractive page styling for Influencer sign up portal & documents (ToS, privacy, etc)
- [ ] Content for Influencer sign-up portal (home view) to give them confidence in the process.
- [x] Content included and structured for Privacy page
- [x] Content included and structured for Tos page
- [ ] Attractive and clear styling for profile and data views seen by Influencers.

### Code Structure, Testing, Clean up

- [x] Setup a real influencer (Noelle Reno) as a confirmed tester.
- [ ] ! Google sheet/drive: Use bacchus service_agent instead of development site service_agent!
- [ ] Test that decide_ig.html form works with the dict as a set value.
- [x] Have real influencer (Noelle Reno) sign up for testing.
- [x] Modularize the codebase: sheets, facebook api, developer_admin, manage
- [ ] Update template to use for-else: in jinja, the else only runs if no iteration
- [x] Modularize the codebase more: move routes elsewhere?
- [x] ? allow logging in related files (remove all print statements) == from flask import current_app as app
- [ ] Update forms and API digesting with input validation to replace following functionality:
  - [x] Currently fix_date used for both create model, and when create_or_update many
  - [x] Currently create_or_update_many also has to modify inputs from Audience API calls
  - [x] Should campaign management view extend base instead of view?
  - [ ] Is current onboard process slow? Delay some data collection?
  - [ ] Other feedback for expected sign up flow?
  - [x] Review data options to confirm our desired data collection.
- [ ] Create Test Users (need a FB page and Instagram business account).
- [ ] Test influencer flow after completion (Have Noelle go through process again)
- [ ] Regex for A1 notation starting cell.
- [x] Code Refactor: move routes to their own files
- [x] Code Refactor: more modular code structure
- [x] Revisit Code Refactor: even more modular code structure?
- [ ] Form Validate: Add method to validate form. Safe against form injection?
- [ ] Error handling on adding user with duplicate email address.
- [ ] Error handling on adding user with duplicate name.
