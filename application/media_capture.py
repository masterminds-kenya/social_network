from flask import flash, current_app as app
# from datetime import datetime as dt
from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument("--test-type")
# options.binary_location = "/usr/bin/chromium"
location = ''
URL = app.config.get('URL')


def get_fullscreen(post, filename):
    """ Visits the permalink for give Post, creates a screenshot named the given filename. """
    ig_url = post.permalink
    driver = webdriver.Chrome(chrome_options=options)
    driver.get(ig_url)
    filepath = location + filename + '.png'
    success = driver.save_screenshot(filepath)
    driver.close()
    message = 'File Saved! ' if success else "Error in Screen Grab. "
    app.logger.debug(message)
    flash(message)
    answer = f"{URL}/{filepath}" if success else f"Failed. {success} "
    return answer
