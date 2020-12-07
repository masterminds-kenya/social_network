# Notes for Development Choices

The following, non-exhaustive references, where discovered and influenced choices made when developing this platform application. Expanding on the main README "Development Notes" section, the "Running Locally ..." section(s) below cover details to help the workflow for developers of this platform application.

## Deploying to Production, Development or Service

The default service, set with the `app.yaml` file, is our deployed production site. The development site and code is being deployed to the `dev` service with the `dev.yaml` file. To create or update a service named `service_name`, we create a `service_name.yaml` file that has a line to set `service: service_name`. Then we run the command below.

``` Bash
    gcloud app deploy [service_name.yaml]
```

If the service setting line is missing, then it assumes it is for the default service. The default service yaml file should be name `app.yaml`.

To view logs of a service:

``` Bash
    gcloud app logs tail -s [service_name]
```

## Useful SQL Queries

If using command line interface for MySQL, these can be helpful for looking for issues with story_metrics hooks/subscriptions and campaign completion status.

### Brands

SELECT brand_id, users.name AS brand, page_id, story_subscribed, campaigns.name AS campaign_name, campaign_id, completed FROM users JOIN brand_campaigns ON users.id = brand_campaigns.brand_id JOIN campaigns ON campaigns.id = brand_campaigns.campaign_id WHERE completed = False ORDER BY story_subscribed, brand;

### Influencers

SELECT user_id, users.name AS influencer, page_id, story_subscribed, campaigns.name AS campaign_name, campaign_id, completed FROM users JOIN user_campaigns ON users.id = user_campaigns.user_id JOIN campaigns ON campaigns.id = user_campaigns.campaign_id WHERE completed = False ORDER BY story_subscribed, influencer;

## Default Env Variables

[App Engine Standard Docs](https://cloud.google.com/appengine/docs/standard/python3/runtime)

| Default Env Variable |  Description |
|:--------------------:|:-----------------:|
| GAE_APPLICATION      | GAE App ID, prefixed with 'region code~' such as 'e~' for Europe deployed.
| GAE_DEPLOYMENT_ID    | The ID of the current deployment.
| GAE_ENV              | The App Engine environment. Set to standard.
| GAE_INSTANCE         | The ID of the instance on which your service is currently running.
| GAE_MEMORY_MB        | The amount of memory available to the application process, in MB.
| GAE_RUNTIME          | The runtime specified in your app.yaml file.
| GAE_SERVICE          | The service name specified in your app.yaml file (or default).
| GAE_VERSION          | The current version label of your service.
| GOOGLE_CLOUD_PROJECT | The Cloud project ID associated with your application.
| NODE_ENV             | Set to production when your service is deployed.
| PORT                 | The port that receives HTTP requests.

## Webhook Updates and Instagram Story Media Metrics

We are using Webhooks to allow Instagram/Facebook to send JSON formatted data to a route on our platform application with updated data. There is a [variety of data we can get with webhooks](https://developers.facebook.com/docs/graph-api/webhooks/reference), and the [process to set this up](https://developers.facebook.com/docs/graph-api/webhooks/getting-started) is fairly similar for each, but the [setup for Instagram](https://developers.facebook.com/docs/instagram-api/guides/webhooks) is a little different.

All influencer users, and most brand users, should have a professional instagram account that is connected to a Facebook business page. In order for our platform to get the most accurate Story metrics, this page needs to have *App* platform enabled (the default setting), and continue to grant `manage_pages` permissions for our platform application (set during our onboarding process using Facebook login). The platform application will [subscribe to the page](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-pages) associated with the instagram account they are using for our platform (subscribing to the page's [name](https://developers.facebook.com/docs/graph-api/webhooks/reference/page/#name) field). There are some additional options for [Page Subscribed Apps](https://developers.facebook.com/docs/graph-api/reference/page/subscribed_apps) should we need it for later development goals. Can do a GET request to see current page subscribed apps. For page subscribed apps, if API version is greater than 3.1, then `subscribed_fields` parameter is required. Also see [Business Login and Page Access](https://developers.facebook.com/docs/facebook-login/business-login-direct) for related notes.

Requirements for live updates by Webhooks for Instagram (STORY updates):

- The app user must have granted your app appropriate Permissions
  - instagram_manage_insights for Stories
  - instagram_manage_comments for Comments and @Mentions.
- The Page connected to the app user's account must have Page subscriptions enabled.
- The Business connected to the app user's Page must be verified.
- Instagram Webhooks must be configured and appropriate Fields subscribed to in the App Dashboard.
- The app must be in Live Mode.
- [IG Docs](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-instagram)

During a given sqlalchemy database session, we are using `session.info` to track which of the current User objects in the session are in need of page and story_metrics subscription. Whenever the `page_token` property is set for a user (triggered by using [SQAlchemy Events](https://docs.sqlalchemy.org/en/13/orm/events.html)), this User object is added to the `session.info` dictionary under the appropriate key indicating it is ready for this process. By waiting to process them until triggered by a `before_flush` session event, we can be certain to have both the `page_token` and `page_id` field values we need. So, just before all these records are saved in the database, the function to send a request to the Graph API to subscribe to the page is called for each of these Users. If page subscription is successful, as expected in most cases, this will set `story_subscribed` as true for a User. When the page is subscribed, our platform will also be subscribed to receive all `story_metrics` for the associated Instagram account. The Instagram Story Media posts, and the API data about them and their metrics, are only available for about 24 hours from when they are published by the user. This `story_metrics` subscription ensures that our platform will be updated with the final metrics data of the Story when it expires.

## Task Queue on Google Cloud Platform

During a given sqlalchemy database session, we are using `session.info` to track which of the current Post objects in the session should be added to a capture task queue. We are using [SQAlchemy Events](https://docs.sqlalchemy.org/en/13/orm/events.html) to notice when a media post is being saved to the database. This Post will be added to the capture queue for stories if the Post is a 'STORY' media post, it does not already have a value for `saved_media` field (indication if we have already captured media image files), and it does not have a value for `capture_name` field (indication if it has already been added to a capture queue). When the Event listener first identifies a targeted STORY post, the Post object is added to an appropriate key in the `session.info` dictionary to be processed later. This slight delay is required since we can not be certain that the Post has set all the values that we need for crafting our Capture API call.

**Outdated starting with version 0.5.1**
Currently the Capture API requires we know the id in the database for this Post. Therefore, the posts targeted for capture in the `session.info` are added to the appropriate Task queue after writing to the database (triggered by a `after_flush_postexec` session event), which also requires an extra round of writing to the database for these objects.

If the Capture API did not require the id in the database for each Post, this process could be made more efficient. We could move the process of populating the Capture Task queue(s) to be triggered by a `before_flush` session event. This would eliminate the extra round of writing to the database since we would be able to make all our needed field updates just before the objects were about to be written.

**With version 0.5.1 and later**
All the processing of `session.info` is handled in response to a `before_flush` session event. This depends on the Capture API not needing to know the id for each Post object, or any other values generated by the database itself.

### Security and Saving Capture Results

[Client for Clouds Task API](https://googleapis.dev/python/cloudtasks/latest/gapic/v2/api.html)

- class google.cloud.tasks_v2.CloudTasksClient(transport=None, credentials=None, client_info=None, client_options=None)
  - create_queue(parent, queue, retry={object object}, timeout={object object}, metadata=None)
  - create_task(parent, task, response_view=None, retry={object object}, timeout={object object}, metadata=None)
  - list_queues(parent, filter_=None, page_size=None, retry={object object}, timeout={object object}, metadata=None)
  - list_tasks(parent, response_view=None, page_size=None, retry={object object}, timeout={object object}, metadata=None)
  - update_queue(queue, update_mask=None, retry={object object}, timeout={object object}, metadata=None)

The following is from [Cloud Task Types](https://googleapis.dev/python/cloudtasks/latest/gapic/v2/types.html)

- class google.cloud.tasks_v2.types.Queue
  - name  # must have following format: projects/PROJECT_ID/locations/LOCATION_ID/queues/QUEUE_ID
  - app_engine_routing_override  # dictionary: service: string, version: string, instance: string
  - rate_limits  # dictionary: max_concurrent_dispatches: integer, max_dispatches_per_second: integer
  - retry_config  # dictionary: max_attempts: integer, max_backoff: string, max_doublings: integer, max_retry_duration: string, min_backoff: string
- class google.cloud.tasks_v2.types.RateLimits
  - max_dispatches_per_second  # same as rate in queue.yaml
  - max_concurrent_dispatches  # same meaning as in queue.yaml
- class google.cloud.tasks_v2.types.RetryConfig
  - max_attempts  # same as task_retry_limit in queue.yaml
  - max_retry_duration  # same as task_age_limit in queue.yaml
  - min_backoff  # same as min_backoff_seconds in queue.yaml
  - max_backoff  # same as max_back0ff_seconds in queue.yaml
  - max_doublings  # same meaning as in queue.yaml
- class google.cloud.tasks_v2.types.AppEngineHttpRequest
  - http_method
  - app_engine_routing  # If app_engine_override is set on the queue, this value is used for all tasks in the queue.
  - relative_uri
  - headers  # some set by GCP, we can add others
  - body  # used for POST or PUT requests
- class google.cloud.tasks_v2.types.AppEngineRouting
  - service
  - version
  - instance
  - host  # Output only. Constructed from the domain name of the app, service, version, instance.

## Other Gcloud Docs and Links

- [Dispatch: url routing](https://cloud.google.com/appengine/docs/standard/python3/reference/dispatch-yaml)
- [Service to Service](https://cloud.google.com/appengine/docs/standard/python3/communicating-between-services)
- [Firewall Settings](https://console.cloud.google.com/networking/firewalls/list?project=engaged-builder-257615)
- [Connector Settings](https://console.cloud.google.com/networking/connectors/list?project=engaged-builder-257615)

## Selenium, testing, and grabbing webpage content for analysis

The 'webdriver' in Selenium appears to be an interface for connecting Selenium either directly to an installed browser, or control an installed browser through a browser driver. So webdriver.CHROME for Chrome and Chromium browsers, webdriver.FIREFOX for FireFox and gecko based browsers, etc. The browser driver code allows further automation and this code package (provided by the makers of those browsers) should be installed. The browser driver code is actually middleware, allowing control over appropriate browser. The browser still needs needs to be installed as well. The desired browser settings, location of the driver, and location of the browser, are passed (or discoverable in the path) to the Selenium webdriver for configuration.

It is unclear if we need a Selenium server running to use a remote WebDriver. This seems to include installing java java package.

There are *many* questions and places of confusion online for getting Chrome, chromedriver, and Selenium all working together. There are many proposed solutions for what seem like the same problem. The most common combinations include the following settings. One or two sources claim that the '--no-sandbox' setting should be listed first.

``` Python
    import chromedriver_binary  # Adds chromedriver binary to path
    from selenium import webdriver

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')
```

When you run Chrome with --remote-debugging-port=9222, it starts an instance with the DevTools protocol enabled. The protocol is used to communicate with Chrome and drive the headless browser instance. [Google Docs Source](https://developers.google.com/web/updates/2017/04/headless-chrome)

``` Python
    options.add_argument("--remote-debugging-port=9222")
```

It is possible to have some experimental options, which take a key, value pair input in the form of `options.add_experimental_option(key, value)`. It seems the `service_args` is a list of args sent to the chromedriver, while the other add_argument values are passed to the actual Chrome browser that is opened. The many other sources and solutions include a wide variety of other options that are less commonly present between them. Here are a few examples that *might* be of value to us:

``` Python
    options.add_argument('blink-settings=imagesEnabled=false')
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--test-type')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('disable-infobars')
    options.add_argument(f"--proxy-server={myProxy}")  # when myProxy in the form of "10.0.x.x:yyyy"
    options.add_argument('--log-level=ALL')
    service_args = ['--verbose', '--log-path=/tmp/chromedriver.log', '--log-level=ALL']
```

The '--disable-gpu' option came up often but but is not needed on most platforms as it is only (maybe an out of date)  requirement applying to only Windows. Xvfb is not needed (any more). Headless Chrome doesn't use a window so a display server like Xvfb is no longer needed. You can happily run your automated tests without it.
[Google Docs Source](https://developers.google.com/web/updates/2017/04/headless-chrome#faq)

Besides the above options, we need the Chrome browser discoverable in the path (or additional settings for driver below). To bring all this together our code needs the following code block example. Some online examples use the deprecated `chrome_options` instead of the more up-to-date `options` keyword. The 'service_args' setting (expects a list) as well as the settings shown set to None, are only needed if we are setting them to some values. The executable_path may be optional if it will be found in the path.
*It is unclear to me if `binary_location` vs `executable_path` is supposed to point to the chromedriver vs path of running the actual Chrome browser. It is not clear to me if we should have only one of these, or both*
Current guess: 1) `options.binary_location = 'usr/bin/chrome'` when 'usr/bin/chrome' is the path to how to actually open and run the browser. 2) `executable_path=chromedriver_binary.chromedriver_filename` to point to the chromedriver file location.

``` Python
    options.binary_location = chromedriver_binary.chromedriver_filename
    # unclear if chromedriver, or chrome for this setting.
    # options.binary_location = "path/to/chrome"
    driver = webdriver.Chrome(executable_path='chromedriver',
                              options=options,
                              service_args=service_args,
                              desired_capabilities=None,
                              service_log_path=None,
                              )
    # Do all the work we want with the driver, such as:
    driver.get(url)
    images = [image.get_attribute('src') for image in driver.find_elements_by_tag_name('img')]
    driver.save_screenshot('screenshot_filename.png')  # save current screen view.
    # etc
    driver.close()
    # driver.quit()  # Is this also needed?
```

### Other Setups, including other Browsers

One tutorial source claimed that instead of using the ChromeOptions approach above, we could use:

``` Python
    from pyvirtualdisplay import Display
    display = Display(visible=0, size=(1024, 768))
    display.start()
    driver = webdriver.Chrome(driver_path=chrome_path, service_args=service_args)
```

There has been mention of using FireFox, which follows a very similar process as Chrome with ChromeOptions above, but using FireFox settings. There was a mention of how proxy settings are different for FireFox, using the following pattern:

``` Python
    firefox_proxy = Proxy({
        'proxyType': ProxyType.MANUAL,
        'httpProxy': myProxy,
        'ftpProxy': myProxy,
        'sslProxy': myProxy,
        'noProxy': ''
    })
    ff_driver = webdriver.Firefox(proxy=firefox_proxy)
```

Besides Chrome and FireFox, there is Selenium phantomjs, which is a headless browser that can be used with the Selenium web automation module.

## String Encoding in MySQL

We are using utf8mb4, not old standard of utf8mb3. This changes our target max characters. To convert:
(old + b) * 0.75 - b = new when b = 1 for old<=255 or 2 for old<=510
old -> new: 255->191, 63->47, 510->382

In MySQL, declaring VARCHAR(num), num is the number of characters.
For utf8mb3 num=255 means it fits without requiring extra reserved bytes
For utf8mb4 mum=191 would be the same as utf8mb3 num=255

MySQL Text storage types:
TINYTEXT 255 bytes (2^8-1)
  If under 255 characters (utfmb3), better than VARCHAR
TEXT 65,535 bytes (2^16-1)
MEDIUMTEXT 16,777,215 bytes (2^24-1)

If the string is less than 255 characters in utf8mb3, TINYTEXT is better.
If using utf8mb4, TINYTEXT can hold 191 characters.
That said, using VARCHAR or SQLAlchemy String makes it more SQL standard.
**Use String(n) for reasonable size text to be portable to other SQL**

### Instagram Strings

Instagram captions **can** be up to 2,200 characters with full utf-8
In MySQL, with utf8mb4, this would be like utf8mb3 of 2933.33 characters
So we need 2^12 to store this (as either utf8mb3 or utf8mb4).
**MySQL TEXT is the correct size for Instragram captions**

Instragram usernames **can** be up to maximum of 30 characters. So even if that assumes full utf-8, for MySQL utf8mb4, it would work to use TINYTEXT or VARCHAR(47), or SQLAlchemey String(47)
**Use String(47) for Instagram usernames**

## Authorization and Encryption

Flask-Login

- [https://scotch.io/tutorials/authentication-and-authorization-with-flask-login]
- [https://flask-login.readthedocs.io/en/latest/]
- [https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-v-user-loginshttps:/]
- [realpython.com/using-flask-login-for-user-management-with-flask/]
- [https://hackersandslackers.com/flask-login-user-authentication/]

Flask-User (says requires Flask-WTF and Flask-Login) focus on role-based authorization.

- [https://flask-user.readthedocs.io/en/latest/index.html]

Flask-Security (uses Flask-Login, Flask-WTF?, Flask-Mail, etc)

- [https://pythonhosted.org/Flask-Security/]

## General Development Notes

Other notes go here.

## Development File Structure

Since we are using pipenv, the local development files, `Pipfile` and `Pipfile.lock`, need to be in the `.gcloudignore` file so they are not pushed to our Google Cloud environments, but still tracked in the Git repository. We want our environment settings stored in a `.env` file and a `app.yaml` file to not be tracked in the Git repository. These files need to be present at the root level so the `config.py`, and potentially other code files, work correctly.

## Running Locally with Remote Database

When running locally, we can proxy the database. This requires a cloud_sql_proxy file, and knowing the DB_CONNECTION_NAME. First make sure the virtual environment running (the `pipenv shell` line). In the terminal, substituting as needed, execute the following command:

``` bash
pipenv shell
./cloud_sql_proxy -instances="DB_CONNECTION_NAME"=tcp:3306
```

Then in another terminal, First make sure the virtual environment running (the `pipenv shell` line). Then at the root of the Repo have flask run the app:

``` bash
pipenv shell
flask run
```

## Connecting to the SQL shell for Remote Database

We can login to the SQL terminal, knowing the correct user and password, with the Google Cloud CLI (replace [DB_INSTANCE] and [username] as appropriate).

```bash
gcloud sql connect [DB_INSTANCE] --user=[username]
```

DEPRECIATED: We can create the database tables by running:

``` bash
python application/model_db.py
```

## Database Migrations

Before upgrading, MAKE SURE our proxy is to the correct database.

If 'FLASK_APP' is not already set in our .env, then in the terminal we need: `export FLASK_APP=main.py`
After that is confirmed set, we can create a migrate file of instructions, and then apply them.
Setup Flask CLI for app, capture DB changes, apply DB changes:

``` bash
flask db migrate
flask db upgrade
```

## Version Updates with Migration

Updates to version 0.6.0

- Styling and site interface updates, including logo and hamburger menu.
- Daily IG media posts downloads limited to Users in currently active Campaigns.
- Security Updates.
- Documentation updates.

Updates to version 0.5.1

- Take site down to ensure we don't miss any work.
- Clone the database. Should be named `bacchusdb-a`, or a different last letter.
- Upload the final code. Make sure it has the final db settings & development mode is off.
- Locally, make sure the `.env` file is connecting to the new DB, as well as local proxy.
- Run `flask db upgrade 01_initial`
- Run `flask run`, then login to admin page. Click the "encrypt" link (also fixes defaults).
- The model_db.User model should be adjusted to have both `token` and `encrypt` fields.
- Run `flask db upgrade 02_after_encrypt`
- The model_db.User model should be adjusted to have the new `token`, but not `encrypt` field.
- The FB console should be updated so everything links to the production site.
- The Capture App should send reports to the production site, or site that called it.
- On the production site, as a dev admin, run the process to subscribe all users.
- Watch the logging for any issues to be followed up for repairs.
