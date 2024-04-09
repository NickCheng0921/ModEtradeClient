"""
Trade handler is named after the major arcana CHARIOT which represents control and action
"""
from __future__ import print_function
import webbrowser
import configparser
from rauth import OAuth1Service
from requests_oauthlib import OAuth1
from accounts.accounts import Accounts
from datetime import datetime
import requests
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

# loading configuration file
config = configparser.ConfigParser()
config.read('config.ini')

OAUTH_REFRESH_MIN = 60 #  from etrade docs, access tokens expire every 2 hours and at midnight by default
OAUTH_RETRY_MIN = 5 #  if we fail to refresh, wait this many minutes and retry
LOGIN_STAGE_WAIT_TIME_SEC = 25

def spoofLogin(website_url):
	options = Options()
	options.add_argument("--window-size=1920,1200")
	driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
	driver.get(website_url)

	user = WebDriverWait(driver, LOGIN_STAGE_WAIT_TIME_SEC).until(
			EC.visibility_of_element_located((By.ID, "USER"))
	)
	pwd = WebDriverWait(driver, LOGIN_STAGE_WAIT_TIME_SEC).until(
			EC.visibility_of_element_located((By.ID, "password"))
	)
	submit = WebDriverWait(driver, LOGIN_STAGE_WAIT_TIME_SEC).until(
			EC.visibility_of_element_located((By.ID, "mfaLogonButton"))
	)

	user.send_keys(config["ACCESS"]["UID"])
	pwd.send_keys(config["ACCESS"]["PWD"])
	submit.click()

	termsSubmit = WebDriverWait(driver, LOGIN_STAGE_WAIT_TIME_SEC).until(
			EC.visibility_of_element_located((By.ID, "acceptSubmit"))
	)

	termsSubmit.click()

	code = WebDriverWait(driver, LOGIN_STAGE_WAIT_TIME_SEC).until(
			EC.visibility_of_element_located((By.XPATH, "//input"))
	)
	if (code):
			code = code.get_attribute("value")
			driver.quit()
			return code
	else:
			driver.quit()
			return None

def oauth():
	"""Allows user authorization for the sample application with OAuth 1"""
	etrade = OAuth1Service(
		name="etrade",
		consumer_key=config["DEFAULT"]["CONSUMER_KEY"],
		consumer_secret=config["DEFAULT"]["CONSUMER_SECRET"],
		request_token_url="https://api.etrade.com/oauth/request_token",
		access_token_url="https://api.etrade.com/oauth/access_token",
		authorize_url="https://us.etrade.com/e/t/etws/authorize?key={}&token={}",
		base_url="https://api.etrade.com")

	base_url = config["DEFAULT"]["PROD_BASE_URL"]

	# Step 1: Get OAuth 1 request token and secret
	request_token, request_token_secret = etrade.get_request_token(
		params={"oauth_callback": "oob", "format": "json"})

	# Step 2: Go through the authentication flow. Login to E*TRADE.
	# After you login, the page will provide a verification code to enter.
	authorize_url = etrade.authorize_url.format(etrade.consumer_key, request_token)
	text_code = spoofLogin(authorize_url)
	
	# Step 3: Exchange the authorized request token for an authenticated OAuth 1 session
	session = etrade.get_auth_session(request_token,
									request_token_secret,
									params={"oauth_verifier": text_code})

	return session, base_url

def renew_session(session):
	renew_url = "https://api.etrade.com/oauth/renew_access_token"
	consumer_key = config["DEFAULT"]["CONSUMER_KEY"]
	consumer_secret = config["DEFAULT"]["CONSUMER_SECRET"]

	auth = OAuth1(consumer_key, consumer_secret, session.access_token, session.access_token_secret)
	response = requests.get(renew_url, auth=auth)

	return response

def get_cash_balance(session, base_url):
	accounts = Accounts(session, base_url)
	cash, _ = accounts.cash_balance_from_account_AUTO()
	return cash
