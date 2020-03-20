from flask import flash, current_app as app
# from datetime import datetime as dt
import time
import re
# import requests
# import urllib.request
# import time
from bs4 import BeautifulSoup as bs
from selenium import webdriver
# import json
from pprint import pprint

location = 'application/save/'
URL = app.config.get('URL')


def chrome_grab(ig_url, filename):
    """ Using selenium webdriver with Chrome and grabing the file from the page content. """
    filepath = location + filename
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--test-type")
    # options.binary_location = "/usr/bin/chromium"

    app.logger.info("==============================================")
    driver = webdriver.Chrome(chrome_options=options)
    driver.get(ig_url)
    success = driver.save_screenshot(f"{filepath}_full.png")
    count = 0 if success else -1
    app.logger.debug(f"Start of count at {count + 1}. ")
    soup = bs(driver.page_source, 'html.parser')
    target = [img.get('src') for img in soup.findAll('img') if not re.search("^\/", img.get('src'))]
    pprint(target)
    for ea in target:
        count += 1
        time.sleep(1)
        try:
            driver.get(ea)
            temp = f"{filepath}_{count}.png"
            app.logger.debug(temp)
            driver.save_screenshot(temp)
        except Exception as e:
            message = f"Error on file # {count} . "
            app.logger.error(message)
            app.logger.exception(e)
            flash(message)
    success = count == len(target)
    message = 'Files Saved! ' if success else "Error in Screen Grab. "
    app.logger.debug(message)
    flash(message)
    answer = f"{URL}/{filepath}_full.png" if success else f"Failed. {success} "
    driver.close()
    return answer


def capture(post, filename):
    """ Visits the permalink for give Post, creates a screenshot named the given filename. """
    ig_url = post.permalink
    answer = chrome_grab(ig_url, filename)
    # response = requests.get(ig_url)
    # app.logger.info(response)
    # soup = bs(response.text, "html.parser")
    # app.logger.info(soup)
    # images = [img.src for img in soup.findAll('img')]
    # app.logger.debug(images)
    # filepath = location + filename
    # file_count = 1
    # for image in images:
    #     # image may be an image file, or it might be a better screenshot page.
    #     urllib.request.urlretrieve(image, f"{filepath}_{file_count}")
    #     file_count += 1
    # success = file_count == len(images)
    # message = 'Files Saved! ' if success else "Error in Capture(s). "
    # app.logger.debug(message)
    # flash(message)
    # answer = f"{URL}/{filepath}" if success else f"Failed. {success} "
    return answer

    # script = body.find('script', text=lambda t: t.startswith('window._sharedData'))
    # page_json = script.text.split(' = ', 1)[1].rstrip(';')
    # data = json.loads(page_json)
