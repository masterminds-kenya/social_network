# Feature Development Plan for June 2020 - ver 0.6.0

## Milestones

| Complete           | Task                                            |
| ------------------ |:-----------------------------------------------:|
|                    | **Initial Features Completion**                 |
| :heavy_check_mark: | Previous Features, see [README](./README.md)    |
|                    | **Milestone 1 Completion:**                     |
| :heavy_check_mark: | Update dependency packages                      |
| :heavy_check_mark: | Onboarding login made quicker, manual user account API calls |
| :heavy_check_mark: | Onboarding not using deprecated `manage_pages`  |
| :heavy_check_mark: | Onboard test: 1 IG account, 2+ IG account       |
| :heavy_check_mark: | Onboard test: No FB pages, No IG on any FB pages|
| :heavy_check_mark: | Onboard test: Add 2nd User                      |
| :heavy_check_mark: | Return Login: 1 User acct, 2+ User acct         |
|                    | **June 2020 Features Completed**                |
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
