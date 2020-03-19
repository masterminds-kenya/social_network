from flask import flash, current_app as app
# from datetime import datetime as dt
from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument("--test-type")
options.binary_location = "/usr/bin/chromium"
location = ''
driver = webdriver.Chrome(chrome_options=options)


def get_fullscreen(post, filename):
    """ Visits the permalink for give Post, creates a screenshot named the given filename. """

    url = post.permalink
    driver.get(url)
    filepath = location + filename + '.png'
    success = driver.save_screenshot(filepath)  # saves in current app location.
    driver.close()
    return success