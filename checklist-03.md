# Feature Development Plan for March 2020 - ver 0.3.0

## Milestones

| Complete           | Task                                         |
| ------------------ |:--------------------------------------------:|
| :heavy_check_mark: | Initial Features from [checklist](./checklist.md) |
|                    | **Initial Features Completed**               |
| :heavy_check_mark: | Initial Investigation of media files complexity |
|                    | Update Feature Goals & Documentation         |
|                    | Separate Dev site owned by Bacchus           |
|                    | Campaign - Sort Posts by published date      |
|                    | Favicon and robots.txt files                 |
|                    | Integrate Flask-Migrate to assist ongoing DB changes |
|                    | **Milestone 1 Completion**                   |
|                    | Update Posts model (db structure) to Many-to-Many w/ campaigns |
|                    | Posts can be assigned to multiple campaigns  |
|                    | Remove dev only logging                      |
|                    | Various code clean-ups & security updates    |
|                    | Migrate & Deploy above updates to live site  |
|                    | **Milestone 2 Completion**                   |
|                    | Saving Story Post media files                |
|                    | View media files associated to a Campaign    |
|                    | **Milestone 3 Completion**                   |
|                    | Story Webhook for full data at expiration    |
|                    | Saving Post media (only if in a Campaign)    |
|                    | Sheet Report layout update, multi-worksheets |
|                    | Attaching media files to data report         |
|                    | Update documentation to capture all updates  |
|                    | **Milestone 4 Completion**                   |
|                    | **March 2020 Features Completed**            |

## Checklist

### Key

- [x] Completed.
- [N] No: does not work or decided against.
- [ ] Still needs to be done.
- [?] Unsure if needed.
- [s] Stretch Goal. Not for current feature plan.

Current Status:
2020-03-12 11:12:23
<!-- Ctrl-Shift-I to generate timestamp -->

### Story & Media Files Features

- [ ] WebHook to get Stories data at completion
  - [ ] Once confirmed, remove story data update from daily cron job
- [ ] Capture Story Post media content files
  - [x] Do not require extra work from Influencers
  - [ ] Capture before story is assigned to campaign, before it expires
  - [ ] Ver A: Investigate if any possible API technique
  - [ ] Ver B: Web Scrapper and screen capture
  - [ ] Ver C: Web Scrapper the obscured media files
- [ ] Associate captured Story media content if it is later assigned to a campaign
- [ ] Non-Story Post media files
  - [x] Current: permalink given. Require manager to screen capture and crop
  - [ ] Capture media file only if associated to a campaign
    - [ ] Use the same technique used for Story media files.

### Campaign & Posts Management

- [ ] Campaign Manage View - Assigning Posts
  - [ ] Posts ordered by published date
  - [ ] Assign & Remove from all Queue
  - [ ] Assign & Keep in all Queue
  - [ ] Un-assign & Add back to all Queue
  - [ ] Un-assign & Remove from all Queue
  - [s] Un-assign & assign to different related campaign

### DB Design & Setup

- [ ] Integrate flask-migrate
  - [ ] Install package, update requirement files
  - [ ] Initial migration creation
  - [ ] test changes and migration management
- [ ] Post model to Campaign is Many-to-Many relationship
  - [ ] Additional fields or methods tracking what queues it is removed from
- [s] Update ON DELETE for a User's posts.
- [s] How do we want to organize audience data?
- [s] Refactor Audience Model to parse out the gender and age group fields
  - [s] After refactor, make sure audience data does not overwrite previous data
- [ ] Encrypt tokens
- [n] Keep a DB table of worksheet ids?
  - [s] Will we have multiple report views?
- [s] DB Migration: Integrate flask-migrate?
- [ ] ?Delete User information in response to a Facebook callback to delete.?
- [x] Allow a user to delete their account on the platform
  - [x] Confirmation page before delete?
  - [ ] What about posts assigned to a campaign?
- [ ] Revisit structure for ON DELETE, ON UPDATE,
- [ ] Revisit structure for how related tables are loaded (lazy=?)
- [ ] Revisit method of reporting Campaign Results.

### Google Drive & Sheets Functionality

- [ ] Improve Google Sheet Report
  - [ ] Export Sheet functions should use multiple worksheets/tabs in the same file.
  - [ ] Check if Google Sheets has a max of 26 columns and 4011 rows (as seemed once).
  - [ ] Regex for A1 notation starting cell.
- [ ] When Export Sheet is created (for Campaign or User), current_user gets sheet permissions
- [s] When Export Sheet is created, access is granted to some universal Admin
- [s] Embed the worksheet as a view in our app (after admin login feature)
- [ ] For a given worksheet, ability to delete existing permissions
- [ ] For a given worksheet, ability to delete the file
- [s] Attach worksheets to the Campaign model so we not always creating new.

### Login & Authentication Features

- [?] Fix brand select an IG account
- [ ] Update User name method
  - [x] Old: temporary name if we do not have one while we are waiting for their IG account selection
  - [ ] ? Use their email address from facebook ?
  - [ ] ? Other plan ?
- [?] Fix: The 'add admin' from admin list does not work because it should redirect.
- [s] Allow admin to create a user w/o a password.
  - [s] Require the user to set password on first login.
- [?] ?Confirm Google login for Worksheet access?
- [s] Auth management features:
  - [s] Change password
  - [s] Recover account (via email)

### Permissions to Routes and Showing/Hiding links in Templates

- [ ] Any Routes / Template views needed to also have limited access?
- [ ] Other Security checks?
- [x] Delete Campaign link limited to just Admin
  - [s] What if a manager accidentally created one?
- [s] Global revoke permissions to all Sheet/file in Drive for a given user

### Site Content & Style

- [s] Update Style for major launch
  - [s] Page styling of admin sections to assist in clear reports and navigation
  - [s] Attractive page styling for Influencer sign up portal & documents (ToS, privacy, etc)
  - [s] Content for Influencer sign-up portal (home view) to give them confidence in the process.
  - [s] Attractive and clear styling for profile and data views seen by Influencers.
- [ ] favicon (looks nice in browser, less search engine errors)
- [ ] Add robots.txt file so search engines are not getting errors.

### Other Site Functionality

- [s] Limit request fetch more Posts to only get new posts since last request
- [s] Fetching Posts - Visual feedback that it is processing but not ready to render new view
- [x] Catch and handle if trying to create an already existing Campaign name
  - [x] Note: Does not update with new inputs I believe
  - [s] Stop and redirect to create new campaign
    - [s] With link to existing campaign of matching name
- [x] Re-Login method for existing account for an Influencer or Brand user
  - [x] Note: Currently a bit of a kludge solution for them to login to existing account
  - [s] TODO: Actual login process does not create and then delete a new account for existing user login
- [s] ?Properly implement Facebook callback to delete some user data ?
- [s] User detail view reports current number of posts we have stored
- [s] Post Detail view
  - [s] Sort or Filter to show posts by processed or not yet processed
  - [s] Sort or Filter to show posts that are assigned to a campaign
  - [s] Sort or Filter to show posts that were rejected from being in a campaign
- [s] Research Google Cloud settings to remove delay for website to spin up after idle.

### Code Structure, Testing, Clean up

- [ ] Setup Dev Version as owned by Bacchus
- [ ] Remove very excessive logs. Keeping high log level until onboarding is verified.
- [ ] Remove excessive logs after we confirm numerous onboarding.
- [ ] Update forms and API digesting with input validation to replace following functionality:
  - [x] Currently fix_date used for both create model, and when create_or_update many
  - [x] Currently create_or_update_many also has to modify inputs from Audience API calls
  - [x] Should campaign management view extend base instead of view?
- [ ] Is current onboard process slow? Delay some data collection?
- [ ] Other feedback for expected sign up flow?
- [ ] Form Validate: Add method to validate form. Safe against form injection?
- [ ] Error handling on adding user with duplicate email address.
- [ ] Error handling on adding user with duplicate name.
