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

- [ ] Pickle tokens
- [n] Keep a DB table of worksheet ids?
  - [s] Will we have multiple report views?
- [s] DB Migration: Integrate flask-migrate?
- [ ] Revisit method of reporting Campaign Results.
- [ ] Revisit structure for ON DELETE, ON UPDATE,
- [ ] Revisit structure for how related tables are loaded (lazy=?)

### Site Functionality

- [?] Decide approach: A) typical form validation & stop submission of existing or B) use existing record.
  - [n] If form validate approach, setup user experience that they can select existing record
  - [x] If incoming form (or API user/brand) already exists, use existing instead of create new:
    - [x] Catch and handle attempt to create a duplicate existing User account
    - [ ] Catch and handle if a User account is trying to add an IG account already used by (another) User account
    - [ ] Catch and handle if trying to create an already existing Campaign name
    - [x] Catch and handle attempt to create a duplicate existing Brand account
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
  - [ ] Calling for more Audience data should also call for update on ig_data metrics.
- [ ] Fetch more Insights (of the account, not of media)
  - [x] Can get a history the the user (or brand) account insights
  - [x] Metrics for 'online_followers' automatically updates with Insight updates.
  - [ ] Will limit request to only get new insights since last request
  - [x] In case we do get duplicates, it will NOT create duplicates in DB
    - [x] Will update if our DB info is out-of-date
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
- [ ] Flash messages for any processes that do not have an obvious update.
  - [ ] Get new posts
  - [ ] get new insights
  - [ ] get new audiences
- [ ] Remove link to get Online Followers Report since it is also called by get insights.
- [ ] Ability to update IG account followers_count and media_count stored in Audience
- [ ] Get new Audience data should also call to get the IG account info (followers_count & media_count).
- [ ] Move/Relabel/remove 'Admin - Log' link on user detail view.
- [ ] More Drive files management
  - [ ] List all files
  - [ ] Manage those files
- [s] Attach worksheets to the Campaign model so we not always creating new.
- [s] Add migration functionality?
- [x] Move hosting and FaceBook settings to Bacchus
- [x] refactor sheets data view to export to a google worksheet
- [ ] Login: any additional User and Admin authentication needed?
  - [ ] ?Confirm Google login for Worksheet access?
  - [ ] ?Add our own App Auth: User management, adding/updating, auth, password, etc.
  - [ ] Admin: only allow admin to see list and (potential) admin views
  - [ ] Research Google Cloud settings to remove delay for website to spin up after idle.

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
