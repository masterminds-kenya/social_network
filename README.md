# social_network

**Author**: Chris L Chapman
**Version**: 0.0.1

## Deployment

Current [Dev Proof-of-Concept Site](https://social-network-255302.appspot.com/)

We are currently deploying on google cloud (gcloud), with a flask server. Gcloud is expecting a pip requirements file (requirements.txt), an app.yaml file (indicating what python version to use, and environment variables), and a main.py file for our server code file. Gcloud also allows an ignore file - `.gcloudignore` which follows the same concepts from `.gitignore` files, as well as additional techniques for allowing files otherwise ignored in the `.gitignore` file. Locally we are using pipenv to help us track dependencies and packages only needed in the development environment. However, the `Pipfile` and `Pipfile.lock` files should be in the ignore file for uploading to gcloud, but still be tracked in the Git repository.

## Development notes

We are expecting an `.env` file at the root of the project so the `config.py` works correctly. For deployment, we also need to update the `app.yaml` file with the appropriate environment variables.

When running locally, we can proxy the database. This requires a cloud_sql_proxy file, and knowing the DB_CONNECTION_NAME. In the terminal, substituting as needed, execute the following command:

``` bash
./cloud_sql_proxy -instances="DB_CONNECTION_NAME"=tcp:3306
```

We can create the database tables by running:

``` bash
python application/model_db.py
```

### Current Feature Development

We are keeping a checklist for features and tasks that are both completed and are upcoming. This is intended as brief overview and to capture ongoing thoughts on how we are proceeding in developing this application. As a living document, it loosely indicates what we plan on working soon, with various degrees of specificity in planning. The current status of this file can be found in the following link:

[Features & Tasks](./checklist.md)

## User Stories

Our application has "Influencer" users who are experts in social media that bring value to our "Brand" company users who are principally responsible for the investment in the reputation of their products, as well as "Marketing" users who further manage this brand reputation investment.

### Influencer - bringing social value

- As an active market influencer for a few years, they have seen growth in social following, and social mentions in the market, which are of great value. However, they are interested and unsure of what clearly defined value this brings their company in sales, conversion or loyalty.
- As a market influencer engaged with a brand, they would like to see the ongoing impact of their campaign efforts has on their audience, the partner brand, and on their own personal branding. This can assist them in fine-tuning and delivering their desired message.
- As an active market influencer beginning new brand relationships, they would like to provide usable and verifiable data on the value they bring to their brand partners.
- As a market influencer, they would like their significant history of influence and reach to be recognized by brands and marketing team members.
- App use: Can easily login with facebook credentials and grant permission to our app
- App use: Can review the permissions and revoke them at any time.
- App use: Can setup the parameters for a campaign (or is this marketing team task?)

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
