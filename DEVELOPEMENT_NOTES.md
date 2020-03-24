# Notes for Development Choices

The following, non-exhaustive references, where discovered and influenced choices made when developing this platform application. Expanding on the main README "Development Notes" section, the "Running Locally ..." section(s) below cover details to help the workflow for developers of this platform application.

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

For Database Migrations:
setup Flask CLI for app, capture DB changes, apply DB changes:

``` bash
export FLASK_APP=main.py
flask db migrate
flask db upgrade
```
