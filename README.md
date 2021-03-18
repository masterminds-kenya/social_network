# social_network

**Author**: Chris L Chapman
**Version**: 0.8.0

This application is a social media analysis platform with "Influencer" users who are experts in social media that bring value to our "Brand" company users who are principally responsible for the investment in the reputation of their products, as well as "Marketing" users who further manage this brand reputation investment.

Influencers benefit by the drastic reduction of campaign reporting required of them. As influencers, they initially give the platform permissions to view their social media content and metrics. Influencers can feel secure that they remain in control of their own social media accounts as the platform does not have access to post or modify content.

Brands benefit from the in-depth metrics for measuring the effectiveness of their campaigns with Influencers. In contrast to common practice in this field, Brands can feel secure that metrics data are accurate and complete, as it comes from the authoritative social media platform and does not rely on the typical manually sent reports that can be incomplete or other risk of inaccurate reporting. Furthermore, this application platform collects and reports more in-depth metrics than many other systems, providing improved analysis.

Marketing users benefit from the automation features of this platform, allowing them to focus on more value-added management and marketing analysis. Marketing user control which content is appropriate for any given campaign through the platforms clear management procedures, and then rely on the platform to appropriately track and report the desired metrics and insights. They can collect metrics and analysis of both the campaign efforts and the brands normal promotional efforts, providing a clearer analysis.

## Architecture

Designed to be deployed on Google Cloud App Engine, using:

- MySQL 5.7
- Python 3.7
- Google Cloud Tasks
- An API for Capture of webpages and images of limited lifespan
  - Our own Capture API service called with secure gRPC protocol
  - [Capture API code](https://github.com/SeattleChris/test-site-content)
- Google Worksheet API v4
- Google Drive API v3
- Facebook Graph API v4.0, with the following scope:
  - pages_show_list
  - instagram_basic
  - instagram_manage_insights

Core packages required for this application:

- flask
- gunicorn
- flask-sqlalchemy
- cryptography
- Flask-Migrate
- flask-login
- pymysql
- google-api-python-client
- google-auth-httplib2
- google-auth
- google-cloud-tasks
- googleapis-common-protos
- requests-oauthlib
- python-dateutil

### Data Collected

The [Instagram (Facebook) Graph API](https://developers.facebook.com/docs/instagram-api) provides information on Instagram Professional accounts and Media (including Stories) posted from those accounts. We collect the following for Influencers and Brand partners who have reviewed and chosen to grant the requested permissions when joining the platform:

- [IG User](https://developers.facebook.com/docs/instagram-api/reference/user)
  - instagram_id
  - username
  - media_count
  - followers_count
- [IG User Insights](https://developers.facebook.com/docs/instagram-api/reference/user/insights) (metrics on the account)
  - impressions (360 days)
  - reach (360 days)
  - online_followers (30 days max, at time of request)
  - Various related to Instagram Profile (90 days)
    - phone_call_clicks
    - text_message_clicks
    - email_contacts
    - get_directions_clicks
    - website_clicks
    - profile_views
    - follower_count
  - audience_city (lifetime metric at time of request)
  - audience_country (lifetime metric at time of request)
  - audience_gender_age (lifetime metric at time of request)
- [IG User Stories](https://developers.facebook.com/docs/instagram-api/reference/user/stories) (list of 'stories' posted in last 24 hours)
  - [FB Dashboard Webhook settings](https://developers.facebook.com/docs/graph-api/webhooks/getting-started#configure-webhooks-product)
  - [Instagram Webhooks](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-instagram)
- [IG User Media](https://developers.facebook.com/docs/instagram-api/reference/user/media) (list of what they have posted)
- [IG Media](https://developers.facebook.com/docs/instagram-api/reference/media) (data on each Media or Stories post)
  - media_type (if not a Stories post)
  - caption
  - comments_count
  - like_count
  - permalink (only valid short term for Stories post)
  - timestamp
  - impressions
  - reach
  - engagement (for IMAGE and VIDEO media types)
  - saved (for IMAGE and VIDEO media types)
  - video_views (for VIDEO media types)
  - carousel_album_engagement (for CAROUSEL_ALBUM media types)
  - carousel_album_saved (for CAROUSEL_ALBUM media types)
  - exits (for Stories)
  - replies (for Stories)
  - taps_forward (for Stories)
  - taps_back (for Stories)

Through our [manually built Facebook Login flow](https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow), we collect the 'facebook_id', which allows us to locate their [Instagram Professional Account(s)](https://help.instagram.com/502981923235522?fbclid=IwAR1pmzAotXJ4X_-XFKNP4Ft2A9F4BuAyMbuFtCZ7ayb3FtLoM7kO6nWQFV4) via [Graph API Page](https://developers.facebook.com/docs/instagram-api/reference/page) route (their Instagram account must be connected to a Facebook Page). If the Influencer or Brand partner has multiple of Instagram Professional accounts, they are given an option of which they want to use for the platform.

The Instagram features of this platform require that Influencer users, and is strongly recommended for Brand users, to have [Instagram Professional Accounts(s)](https://help.instagram.com/502981923235522?fbclid=IwAR1pmzAotXJ4X_-XFKNP4Ft2A9F4BuAyMbuFtCZ7ayb3FtLoM7kO6nWQFV4). The platform is also depending on this account being [connected to a business Facebook page](https://www.facebook.com/business/help/898752960195806), as is customary for professional Instagram accounts. During the platform onboarding process, influencer and brand users use Facebook login to grant the platform various permissions for their Instagram account and connected Facebook page. The platform aims to only request the permissions needed. The platform's automation features will be unreliable for a user or behave in unexpected ways if the user changes and removes these requested permissions.

In order for our platform to get the most accurate Story metrics, the following conditions must be met:

- The Page connected to the app user's account must have Page subscriptions enabled.
- The Business connected to the app user's Page must be verified.
- The user must have granted us instagram_manage_insights as requested in onboarding.
- ? The Page connected to the app user's account must have *App* platform enabled (the default setting)?
  - Check in their [App Settings](https://www.facebook.com/settings?tab=applications) for the page.
- ? Old: The user must grant `manage_pages` as requested in onboarding?
- ? The user must grant `pages_read_engagement` as requested in onboarding?

## Requirements, and links to Graph API Permissions and Structures

When looking at techniques and Documentation, be careful and **DO NOT USE** the Instagram Basic Display API, it is an incorrect source. Make sure to **USE Instagram Graph API** for documentation (links below).

- Do NOT use: [Instagram Basic Display API](https://developers.facebook.com/docs/instagram-basic-display-api/overview/permissions#instagram-graph-user-media)
  - "Apps designated as Business apps are not supported. If your app is a Business app use the Instagram Graph API instead, or create a new, non-Business app." [AppTypes](https://developers.facebook.com/docs/instagram-basic-display-api/overview#instagram-user-access-tokens)
  - `instagram_graph_user_media` allows reading Media node (for an image, video, or album) and edges.
  - `instagram_graph_user_profile` permission allows your app to read the app user's profile.

The following includes links and critical requirements.
TODO CRITICAL: For all Graph API results, the BIP App must handle pagination results in the response.

- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api)
  - Limitations
    - Not for IG consumer accounts, only for Business or Creator Instagram accounts
    - IGTV and Reels are not supported.
    - Ordering results is not supported.
    - All endpoints support cursor-based pagination.
    - Only User Insights edge supports time-based pagination.
  - [Overview](https://developers.facebook.com/docs/instagram-api/overview)
    - Users & Tokens: handled indirectly through Facebook accounts.
      - They must have an IG Professional account, connected to a Facebook account (our App needs FB login).
      - They must have a Facebook Page connected to the Instagram Professional account.
      - The must have [Page subscriptions enabled](https://developers.facebook.com/docs/instagram-api/guides/docs/instagram-api/guides/webhooks#step-2--enable-page-subscriptions) Note: broken link provided by Docs.
      - Their Facebook login must be able to perform admin-equivalent Tasks on that FB Page.
      - [Admin-equivalent Tasks](https://developers.facebook.com/docs/instagram-api/overview#tasks)
      - Not [Business Manager System Users](https://developers.facebook.com/docs/marketing-api/system-users)
    - [EU Insights Limitations](https://developers.facebook.com/docs/instagram-api/guides/insights):
      - Stories `replies` metric does not include data from or to those in European Economic Area
    - Timestamps: use UTC, zero offset, ISO-8601 format, e.g. 2019-04-05T07:56:32+0000
    - [Webhooks for Instagram](https://developers.facebook.com/docs/instagram-api/guides/webhooks)
      - The IG Professional user's connected Facebook Page must have Page subscriptions enabled.
      - We need the IG Professional user's Page Access Token
      - We must have the `pages_manage_metadata` permission.
      - This [App must subscribe](https://developers.facebook.com/docs/graph-api/reference/page/subscribed_apps#Creating) to the IG user's FB Page
      - `story_insights` - sent when the story expires, only gives update of metrics.
      - `comments` (on media post owned by IG user) and `mentions` for @account in comment or caption.

## Deployment

[Deployed Site](https://www.bacchusinfluencerplatform.com)

We are currently deploying on google cloud (gcloud), with the Google App Engine standard environment. Some packages and code would need to be modified if we switched to App Engine flex, or other gcloud deploy services. Google Cloud (GCloud) is expecting a pip requirements file (`requirements.txt`), a `app.yaml` file (indicating what python version to use, and environment variables), and a `main.py` file as a point of entry for the application server to run. Gcloud also allows an ignore file - `.gcloudignore` which follows the same concepts from `.gitignore` files, as well as additional techniques for allowing files otherwise ignored in the `.gitignore` file.

This platform application also depends on the [Capture API](https://github.com/SeattleChris/test-site-content) application running. This platform calls the Capture API as a service to record confirmation of content. This service API is also hosted on Google Cloud Platform, and is a part of the same project that our platform application belongs to.

## Development Notes

[Development Site](https://dev-dot-engaged-builder-257615.appspot.com)

We are using pipenv, for local development, to help us track both dependencies and packages only needed in the development environment and those needed for the deployed environment. For running locally, we utilize `cloud_sql_proxy` for database connections. We are using the `gcloud` CLI for connecting and managing our Google Cloud development and deployed sites. More development tools and notes can be found in [Development Notes](./DEVELOPEMENT_NOTES.md) section.

### Current Feature Development

We are keeping a checklist for features and tasks that are both completed and are upcoming. This is intended as brief overview and to capture ongoing thoughts on how we are proceeding in developing this application. As a living document, it loosely indicates what we plan on working soon, with various degrees of specificity in planning. The current status of this file can be found in the following link:

- [Features & Tasks - Round 3](./checklist-07.md) for up to version 0.7.0.
- [Login - Onboarding Update](./checklist-06.md) for up to version 0.5.5.
- [Features & Tasks - Round 2](./checklist-03.md) for up to version 0.5.0.
- [Original Features & Tasks](./checklist.md) for up to version 0.2.0.

## Core Features

### Influencer and Brand user Onboarding

An influencer or brand partner can join the platform by following the link/button from the home page. This will lead them to verify with Facebook that they grant permission to the platform to look into the metrics and activity on their business Instagram account. This is required for influencers, enabling the platform to take care reporting metrics. It is optional, but highly recommended, for brand partners to also join with their business Instagram account. If brand users choose this option, they will receive additional metrics and analysis in their campaign reports. The granting of these permissions requires that the influencer (or brand using this process) has a business Instagram account that is connected to a Facebook page, as is the typical expectation for these professional accounts.

Joining the platform does not grant access to other non-partnered influencers or brands. Joining the platform does grant other influencers or brands to their own account information outside of the platform admin & managers and the partnerships that influencer and brand partners enter in together.

### Manager and Admin Onboarding

The typical process of adding a new manager or admin requires approval, and is initiated, by someone with an existing admin account. The initial admin accounts are setup at the launch of the platform. Later admin or manager accounts are first created by an existing admin who then sends an invite to the new manager or admin. When these new users login for the first time they will need to provide a password and confirm or update their email address that they will use for verifying their access. If this email address is one that is connected to google drive or GSuite features (typically a gmail account, or other email managed through google), it will make it easier when they are later accessing any generated google sheets (or they can grant themselves access later if their login email does not match). The access to the platform can be revoked by the platform admins.

### Access to Influencer, Brand, or Campaign Data and Metrics

Campaigns, which are mutually agreed on relationships between influencers and brand partners, are created and processed by admin and managers. Only Bacchus staff and approved consultants have access to manage and generate reports for a campaign. These reports are delivered to influencers and brands for campaigns they are involved with, to better understand how the campaign performs.

Influencers and brand partners have access to the data collected on their account. They are not given open access to the all the data on other influencers or on other brands, even if they have a partnership through a campaign. Brands (and influencers) are given a report of how a campaign performs. This report includes details about the influencers (and brand partners) in this campaign, but it is not granting excessive access permission to look into the influencers (or brand partner) data in a way that is out of scope for their partnership.

### Delivering Data and Metrics

Initially, influencers, and brand partners, grant permissions for the platform to view their instagram accounts. Once they have agreed on a campaign partnership, the collecting and managing of the performance data is done through automated and managed processes by platform admin and managers. Influencers do not need to worry about capturing screenshots or sending email reports, as the needed information is available to the platform staff. The platform admin and managers, through the tools of the platform, are responsible for managing and generating the reports to be delivered to the brand partners and influencers.

## User Stories

Our application has "Influencer" users who are experts in social media that bring value to our "Brand" company users who are principally responsible for the investment in the reputation of their products, as well as "Marketing" users who further manage this brand reputation investment.  Brands wish to measure the effectiveness of their Influencer campaigns; such measurement and reporting is done manually, requiring contacting each Influencer.  This app will automate reporting and bring more measurement capabilities to Bacchus and the Brands.

### Influencer - bringing social value

- As an active market influencer for a few years, they have seen growth in social following, and social mentions in the market, which are of great value. However, they are interested and unsure of what clearly defined value this brings their company in sales, conversion or loyalty.
- As a market influencer engaged with a brand, they would like to see the ongoing impact of their campaign efforts has on their audience, the partner brand, and on their own personal branding. This can assist them in fine-tuning and delivering their desired message.
- As an active market influencer beginning new brand relationships, they would like to provide usable and verifiable data on the value they bring to their brand partners.
- As a market influencer, they would like their significant history of influence and reach to be recognized by brands and marketing team members.
- App use: Can easily login with facebook credentials and grant permission to our app
- App use: Can review the permissions and revoke them at any time
- App use: Can view metrics relating to their own account
- App use: Outside of onboarding, additional ongoing tasks are not needed

### Brand - Deciding where to invest

- As a brand company active with market influencers for a a few years, they are satisfied that their influencer activity brings significant value to their brand. However, they feel their influencer strategy could be optimized, especially as the market becomes more crowded and competitive. The brand company wants to know how to leverage influencer campaigns in their overall marketing strategy, by amplifying and tracking gained users.
- As a brand company that has been active in influencer marketing for a few years, they are concerned with the rising prices for both influencer campaigns and for social paid ads. The brand company wants to invest their budget where the most impact can be gained. However, they do not have the data on either to understand and determine their best options.
- A given brand company has resisted influencer marketing for a decade, but has previously benefited from organic reach. They are seeking advice on how to use other channels - earned and paid - so they do not lose market share.
- As a brand company without a strong social marketing history, they are cautiously new to paid social and they are skeptical about influencer marketing. They want to invest in both, but need measurable systems with clearly defined data to justify investment in this typically fuzzily defined field driven by vanity metrics.

### Marketing - Manager of the Campaign

- As a marketer who has been active with social influencers for a few years, they have historically seeded/sampled/gifted product or paid for product placement in an influencer feed. They are unsure the actual ROI and is looking to understand which influencers bring the most real quality audience/customers.
- As a marketer who is relatively new to influencer marketing, they answer to senior leadership who want clearly defined measurable results. This influencer marketing campaign must be comparable with all their other marketing opportunities, with all projects ladder up to a 360* digital eco-system. Without enough data on influencer campaigns, the marketing team cannot justify investment compared to their other clearly defined digital strategies.
- App use: Can view useful and clearly defined data using google worksheets.
- App use: They know they are viewing reliable and accurate data.
- App use: Uses the platform's interface to manage Campaigns and Posts assigned to them.
- App use: Can assign posts to multiple Campaigns if needed.
- App use: Campaigns can include one or many Brands and include one or many Influencers.
- App use: Does not need to issue commands or modify the code for the data they want.
- App use: Campaign reports give data and access to media file content.
