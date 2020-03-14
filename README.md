# social_network

**Author**: Chris L Chapman
**Version**: 0.3.0

## Architecture

Designed to be deployed on Google Cloud App Engine, using:

- MySQL 5.7
- Python 3.7
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
- Flask-Migrate
- flask-login
- pymysql
- google-api-python-client
- google-auth-httplib2
- google-auth
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

## Deployment

[Deployed Site](https://www.bacchusinfluencerplatform.com)

We are currently deploying on google cloud (gcloud), with the Google App Engine standard environment. Some packages and code would need to be modified if we switched to App Engine flex, or other gcloud deploy services. Google Cloud (GCloud) is expecting a pip requirements file (`requirements.txt`), a `app.yaml` file (indicating what python version to use, and environment variables), and a `main.py` file as a point of entry for the application server to run. Gcloud also allows an ignore file - `.gcloudignore` which follows the same concepts from `.gitignore` files, as well as additional techniques for allowing files otherwise ignored in the `.gitignore` file.

## Development notes

[Development Site](https://devfacebookinsights.appspot.com)

For local development, we are using pipenv to help us track dependencies and packages only needed in the development environment. The local development files, `Pipfile` and `Pipfile.lock`, need to be in the `.gcloudignore` file, but still tracked in the Git repository. We are expecting an un-tracked `.env` file at the root of the project so the `config.py` works correctly, locally while these same settings should be duplicated in the `app.yaml` for the deployed site to work.

When running locally, we can proxy the database. This requires a cloud_sql_proxy file, and knowing the DB_CONNECTION_NAME. In the terminal, substituting as needed, execute the following command:

``` bash
./cloud_sql_proxy -instances="DB_CONNECTION_NAME"=tcp:3306
```

We can login to the SQL terminal, knowing the correct user and password, with the Google Cloud CLI (replace [DB_INSTANCE] and [username] as appropriate).

```bash
gcloud sql connect [DB_INSTANCE] --user=[username]
```

We can create the database tables by running:

``` bash
python application/model_db.py
```

### Current Feature Development

We are keeping a checklist for features and tasks that are both completed and are upcoming. This is intended as brief overview and to capture ongoing thoughts on how we are proceeding in developing this application. As a living document, it loosely indicates what we plan on working soon, with various degrees of specificity in planning. The current status of this file can be found in the following link:

- [Features & Tasks ver 0.3.0](./checklist-03.md)
- [Original Features & Tasks](./checklist.md)

## Core Features

### Influencer and Brand user Onboarding

From the home page, an influencer or brand partner can join the platform by following the link/button from the home page. This will lead them to verify with Facebook that they grant permission to the platform to look into the metrics and activity on their business Instagram account. This is required for influencers, but there is an option for brand partners to join without their own instagram account (but limiting some of the platform features they gain from that connection). The granting of these permissions requires that the influencer (or brand using this process) has a business Instagram account that is connected to a Facebook page, as is the typical expectation for these professional accounts.

Joining the platform does not grant access to other non-partnered influencers or brands. Joining the platform does grant other influencers or brands to their own account information outside of the platform admin & managers and the partnerships that influencer and brand partners enter in together.

### Manager and Admin Onboarding

The typical process of adding a new manager or admin requires approval, and is initiated, by someone with an existing admin account. The initial admin accounts are setup at the launch of the platform. Later admin or manager accounts are first created by an existing admin who then sends an invite to the new manager or admin. When these new users login for the first time they will need to provide a password and confirm or update their email address that they will use for verifying their access. If this email address is one that is connected to google drive or GSuite features (typically a gmail account, or other email managed through google), it will make it easier when they are later accessing any generated google sheets (or they can grant themselves access later if their login email does not match). The access to the platform can be revoked by the platform admins.

### Access to Influencer, Brand, or Campaign Data and Metrics

Campaigns, which are mutually agreed on relationships between influencers and brand partners, are created and processed by admin and managers. Only Bacchus staff and approved consultants have access to manage and generate reports for a campaign. These reports are delivered to influencers and brands for campaigns they are involved with, to better understand how the campaign performs.

Influencers and brand partners have access to the data collected on their account. They are not given open access to the all the data on other influencers or on other brands, even if they have a partnership through a campaign. Brands (and influencers) are given a report of how a campaign performs. This report includes details about the influencers (and brand partners) in this campaign, but it is not granting unlimited access permission to look into the influencers (or brand partner) data in a way that is out of scope for their partnership.

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
- App use: Can view useful and clearly defined data using google worksheets
- App use: They know they are viewing reliable and accurate data.
- App use: Does not need to issue commands or modify the code for the data they want
- App use: Campaign reports give data and access to media file content
