# Feature Development Plan for July 2020 - ver 0.7.0

## Milestones

| Complete           | Task                                            |
| ------------------ |:-----------------------------------------------:|
|                    | **Initial Features Completion**                 |
| :heavy_check_mark: | Previous Features, see [README](./README.md)    |
|                    | Proposal and quotes for upcoming features       |
|                    | **Milestone 1 Completion**                      |
|                    | Refactor all to no longer need `manage_pages`   |
|                    | App can request User for missing permissions    |
|                    | App monitors permissions to determine new requests|
|                    | Update permission scope for existing users      |
|                    | Campaigns can have a start and end date         |
|                    | Auto-populate default dates & have date selector|
|                    | Campaigns active status determined by date range|
|                    | Get Posts only for Users in active Campaigns    |
|                    | Story Metrics only for Users in active Campaigns|
|                    | **Milestone 2 Completion**                      |
|                    | Capture Story images only if in active Campaigns|
|                    | Queue setup for requests to Capture service     |
|                    | Capture service manages digesting queue         |
|                    | Capture service saves media images to bucket    |
|                    | Determine capture timing for story images       |
|                    | Capture service reports success results         |
|                    | Successful Captures are recorded in DB          |
|                    | Managers can review captured story images       |
|                    | Managers can select best image amongst options  |
|                    | Managers can request urgent recapture on Stories|
|                    | Managers can request Capture on non-Story posts |
|                    | Queue setup for non-story capture requests      |
|                    | Capture service digests non-story queue         |
|                    | Determine capture timing for non-story images   |
|                    | Non-story captures reported and recorded in DB  |
|                    | Managers can review & select non-story captures |
|                    | **Milestone 3 Completion**                      |
|                    | Scale: batches for daily Requests of Posts      |
|                    | Security: Capture requests only on gRPC protocol|
|                    | Campaign sheet reports include saved media links|
|                    | Sheet permission given to user creating it      |
|                    | Default user who always gets Sheet access       |
|                    | Sheet management: Delete, Modify access, etc    |
|                    | More efficient run of Capture Service/servers   |
|                    | Update Docs on all features                     |
|                    | Update Production site & confirm features       |
|                    | **Previously Completed Stretch Goals**          |
| :heavy_check_mark: | Security: encrypting stored tokens              |
| :heavy_check_mark: | Separate Capture application & resources        |
| :heavy_check_mark: | On User delete, remove metrics & keep Posts     |
| :heavy_check_mark: | Admin feature: check permissions a User granted |
| :heavy_check_mark: | Capture app self-updates OS and Browser         |
|                    | **Possible Features & Goals**                   |
|                    | Post model has is_story separate from media_type|
|                    | User metrics collected at Campaign end|start    |
|                    | On user delete, only delete non-campaign posts  |
|                    | Process for deleting unneeded captured images   |
|                    | New manager/admin account password set on first login |
|                    | Onboarding: Paginated results on IG accounts    |
|                    | Handle a User delete request from Facebook      |
|                    | Tests: ensure future dev doesn't break existing functions |
|                    | **July 2020 Features Completed**                |
|                    | Migrate live DB (and deploy all of above)       |
|                    | Run functions needed for migrate steps          |
|                    | Confirm Onboarding & new features               |

## Checklist

### Key

- [x] Completed.
- [n] No: does not work or decided against.
- [ ] Still needs to be done.
- [c] Needs to be confirmed.
- [?] Unsure if needed.
- [s] Stretch Goal. Not for current feature plan.

Current Status:
2020-06-15 01:29:58
<!-- Ctrl-Shift-I to generate timestamp -->

### Login & Authentication Features

- [x] Faster Onboarding: Remove user account metrics collection from onboarding process.
  - [x] Removed from onboarding function.
  - [x] Confirm there is a manual button for all API calls removed from onboarding.
- [ ] Updates for deprecated manage_pages permission.
  - [ ] Lookup permissions of all current users to see if they have `manage_pages` or replaced permissions.
  - [ ] Confirm `pages_read_engagement` works where we previously needed `manage_pages`.
    - [c] To see accounts (pages this user has a role on), our `pages_show_list` permission is sufficient.
    - [c] We can still find the `instagram_business_account` as previously worked for onboarding.
    - [ ] See if we need to find `connected_instagram_account` as described in [Page](https://developers.facebook.com/docs/graph-api/reference/page/).
    - [ ] ?Do we need to consider [assigned_pages](https://developers.facebook.com/docs/graph-api/reference/user/assigned_pages/)?
    - [ ] Does our app need the Feature: [Page Public Content Access](https://developers.facebook.com/docs/apps/review/feature#reference-PAGES_ACCESS).
    - [ ] We can still subscribe to the page (if confirmed it is needed).
    - [ ] Confirm we can still subscribe to a users `story_metrics`.
    - [ ] Check other places we depended on `manage_pages`.
    - [ ] ? Needed?: Determine processes for old user accounts updating their permissions.
- [?] Fix brand select an IG account.
- [s] Update User name method.
  - [x] Old: temporary name if we do not have one while we are waiting for their IG account selection.
  - [s] ? Use their email address from facebook ?
  - [s] ? Other plan ?
- [c] Fix: The 'add admin' from admin list does not work because it should redirect.
- [s] Allow admin to create a user w/o a password.
  - [s] Require the user to set password on first login.
- [?] ?Confirm Google login for Worksheet access?
- [s] Auth management features:
  - [s] Change password.
  - [s] Recover account (via email).

### Collect data only if needed for an active Campaign

- [ ] Story Metrics only subscribed for users currently in an active Campaign.
  - [ ] List all users in active campaign, if not subscribed then add to subscribe list/queue.
  - [ ] List all users not in active campaign & currently subscribed, then add to unsubscribe list/queue.
- [ ] Remove story metrics update from daily cron job.
- [ ] Daily cron of posts, only if user is in a currently active campaign.
- [ ] Update Campaign model with a start and end date (UTC Timestamp).
- [ ] Set a default Campaign end date that can be updated by staff.
- [ ] Manage Campaign active status:
  - [ ] Option 1) All managed by active dates: If before expire AND (after start OR created date).
  - [ ] Option 2) Process to switch Campaign.completed bool; possible end of Campaign processes.
- [ ] Create process to automatically collect User account metrics if User is in a campaign.
  - [ ] ? When to collect: Campaign end | Campaign start | User assigned to uncompleted Campaign?

### Capture Media Image Files for Stories

- [x] Do not require extra work from Influencers
- [x] Create a separate media capture service (GCP App Engine - Flex environment) and API
  - [x] Create Dockerfile that builds on python3.7, installs Chrome and & Chromedriver
    - [x] Dockerfile is self-maintaining for Chrome, installs up-to-date stable version.
    - [x] Dockerfile can determine correct chromedriver, install and configure as needed.
    - [x] Dockerfile is self-maintaining for linux, python3.7, chrome, chromedriver.
    - [ ] Tests run after update in Chrome or any packages.
  - [x] Captured media storage to Storage bucket and reports a url link.
- [x] Associate captured Story media content if it is later assigned to a campaign.
- [c] Process Capture service response, associating captured media urls to the related Post.
- [c] Campaign sheet report includes a column for this captured and saved media content.
- [s] Non-Story Post media files.
  - [x] Current: permalink given. Require manager to screen capture and crop.
  - [?] If manually captured, include it in Campaign reports.
  - [s] Capture media file only if associated to a campaign.
    - [s] Use the same technique used for Story media files.
- [s] Process for releasing and deleting saved media files.
  - [s] At what point is a Story old enough, and still not in a Campaign, it should be deleted?
  - [s] Should we delete or put into some other long-term storage for old Campaign media files?
- [x] Document in API that 'saved_media' and 'post_model' are reserved keys in response.
- [n] Capture before story is assigned to campaign, before it expires.
  - [x] Temp solution: attempt capture when created or updated.
  - [?] Better solution: add to Task Queue to Capture.
- [ ] Task Queue to manage calling the Capture API.
  - [x] Able to create a task queue to capture stories.
  - [?] Able to create a task queue to capture other posts.
  - [x] Able to use existing task queue (story or post captures).
  - [x] Able to add a task to a capture queue.
  - [ ] Activate Task Queues for Story and for any manually added Posts.
  - [ ] ? Need to call update_queue when adding a task to keep extending the queue expiration.
  - [?] Determine and set appropriate retry settings, especially for Story captures.
  - [x] Post model has field(s) for tracking and reporting captured media image links.
  - [ ] Update Post instances with links to the captured media images.
    - [ ] Another queue to read completed capture queue tasks?
    - [ ] ? Refactor capture queue to route on current app service (default for prod, dev for dev)?
- [s] Determine options for video files.
  - [s] Can we grab the entire video?
  - [s] Can we grab a frame of the video, or default view?

Also see items in the [test-site-content checklist](https://github.com/SeattleChris/test-site-content/blob/master/checklist.md)

### Campaign Views - Assigning Posts

- [x] Reject & remove from only this Campaign List
- [x] Un-assign & Add back to this Campaign List
- [x] Un-assign & Remove from this Campaign List
- [x] Assign & Keep in all Campaign Lists
- [n] Assign & Remove from all Campaign Lists
- [n] Un-assign & Add back to all Campaign List
- [n] Un-assign & Remove from all Campaign List
- [s] Un-assign & assign to different related campaign
- [?] Update & Improve wording for processing Campaign Posts
- [x] View and modify Posts that had been rejected for this campaign
- [?] In all Campaign views, report what other Campaigns a Post belongs to if any
- [s] Cleaner written template radio input logic: if a view then value=0 checked, else other value

### DB Design & Setup

- [s] Update ON DELETE for a User's posts.
- [s] How do we want to organize audience data?
- [s] Refactor Audience Model to parse out the gender and age group fields
  - [s] After refactor, make sure audience data does not overwrite previous data
- [x] Set order_by='recorded' inside db.relationship declarations?
  - [x] Confirm this does not break templates somehow?
- [n] Keep a DB table of worksheet ids?
  - [s] Will we have multiple report views?
- [s] DB Migration: Integrate flask-migrate?
- [s] ?Delete User information in response to a Facebook callback to delete.?
- [x] Allow a user to delete their account on the platform.
  - [x] Confirmation page before delete?
- [ ] Campaign Model has start and end date, active status determined by date.
  - [ ] What about posts assigned to a campaign?
    - [x] Keep all old posts.
    - [x] Campaign collected can still see posts from deleted users if already in campaign.
    - [x] Campaign results still works with posts from deleted users.
    - [?] Campaign sheet report still works with posts from deleted users.
    - [s] Keep posts only currently in a campaign, discard unattached posts.
  - [ ] What about unassigned posts for this User?
    - [s] Each post should be deleted.
    - [?] Any reference to this post (Campaign.processed) should be handled ON DELETE.
- [c] Revisit structure for ON DELETE, ON UPDATE (especially on User delete).
- [c] Revisit structure for how related tables are loaded (lazy=?).
- [s] Revisit method of reporting Campaign Results.

### Google Drive & Sheets Functionality

- [x] Captured media content is accessible from the Google Sheet report.
  - [c] ? Link to the content ?
  - [s] ? Embed the content ?
- [s] Regex for A1 notation starting cell.
- [ ] When Export Sheet is created (for Campaign or User), current_user gets sheet permissions
- [ ] When Export Sheet is created, access is granted to some universal Admin
- [s] Embed the worksheet as a view in our app (after admin login feature)
- [s] For a given worksheet, ability to delete existing permissions
- [s] For a given worksheet, ability to delete the file
- [s] Attach worksheets to the Campaign model so we not always creating new.

### Permissions to Routes and Showing/Hiding links in Templates

- [x] Delete Campaign link limited to just Admin.
  - [s] What if a manager accidentally created one?
- [s] Global revoke permissions to all Sheet/file in Drive for a given user.

### Site Content & Style

- [s] Update Style for major launch.
  - [s] Page styling of admin sections to assist in clear reports and navigation.
  - [s] Attractive page styling for Influencer sign up portal & documents (ToS, privacy, etc).
  - [s] Content for Influencer sign-up portal (home view) to give them confidence in the process.
  - [s] Attractive and clear styling for profile and data views seen by Influencers.
- [x] favicon (looks nice in browser, less search engine errors).
- [x] Confirm all templates build off a template that points to favicon location.
  - [x] extends "base.html" is safe.
  - [x] extends "view.html" is safe.
  - [x] extends "campaign.html" is safe.
  - [x] All template files are extensions of base or other confirmed sources.
- [?] Error response using template vs app.errorhandler(500).
- [?] Turn off the extra info for an error 500 for deployed live site.
- [x] Add robots.txt file so search engines are not getting errors.

### Other Site Functionality

- [s] Limit request fetch more Posts to only get new posts since last request.
- [s] Fetching Posts - Visual feedback that it is processing but not ready to render new view.
- [x] Catch and handle if trying to create an already existing Campaign name.
  - [x] Note: Does not update with new inputs I believe.
  - [s] Stop and redirect to create new campaign.
    - [s] With link to existing campaign of matching name.
- [x] Re-Login method for existing account for an Influencer or Brand user.
  - [x] Note: Currently a bit of a kludge solution for them to login to existing account.
  - [s] TODO: Actual login process does not create and then delete a new account for existing user login.
- [s] ?Properly implement Facebook callback to delete some user data ?
- [s] User detail view reports current number of posts we have stored.
- [s] Post Detail view.
  - [s] Sort or Filter to show posts by processed or not yet processed.
  - [s] Sort or Filter to show posts that are assigned to a campaign.
  - [s] Sort or Filter to show posts that were rejected from being in a campaign.
- [s] Research Google Cloud settings to remove delay for website to spin up after idle.

### Code Structure, Testing, Clean up

- [ ] Remove very excessive logs. Keeping high log level until onboarding is verified.
  - [ ] Modify to use logger.debug as appropriate
  - [ ] Modify to use logger.exception as appropriate
  - [ ] Modify to use logger.info as appropriate
  - [ ] Change settings so live site does not log DEBUG
  - [ ] ? Change settings so live site does not log INFO ?
- [c] Remove excessive logs after we confirm numerous onboarding.
- [?] Check and comply to expected response on a cron job.
- [ ] Migrate Live DB (test with having Dev site connect to it before deploy live code?)
- [ ] Set DEV_RUN=False, and deploy to live site.
- [s] Update forms and API digesting with input validation to replace following functionality:
  - [x] Currently fix_date used for both create model, and when create_or_update many
  - [x] Currently create_or_update_many also has to modify inputs from Audience API calls
  - [x] Should campaign management view extend base instead of view?
- [c] Is current onboard process slow?
- [c] Other feedback for expected sign up flow?
- [s] Form Validate: Add method to validate form. Safe against form injection?
- [s] Error handling on adding user with duplicate email address.
- [s] Error handling on adding user with duplicate name.
