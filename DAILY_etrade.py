"""This Python script provides examples on using the E*TRADE API endpoints"""
from __future__ import print_function
import webbrowser
import logging
import configparser
from rauth import OAuth1Service
from logging.handlers import RotatingFileHandler
from accounts.accounts import Accounts
from market.market import Market
from datetime import datetime
from order.order import Order

import triton_config
import AUTO_orders

# loading configuration file
config = configparser.ConfigParser()
config.read('config.ini')

ORDER_FILE = triton_config.ORDER_FILE_NAME
#SLEEP_TIME_MINUTES = 3

# logger settings
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler("python_client.log", maxBytes=5*1024*1024, backupCount=3)
FORMAT = "%(asctime)-15s %(message)s"
fmt = logging.Formatter(FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p')
handler.setFormatter(fmt)
logger.addHandler(handler)


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
	webbrowser.open(authorize_url)
	print(authorize_url)
	text_code = input("Please accept agreement and enter verification code from browser: ")

	# Step 3: Exchange the authorized request token for an authenticated OAuth 1 session
	session = etrade.get_auth_session(request_token,
									request_token_secret,
									params={"oauth_verifier": text_code})

	main_loop(session, base_url)

def main_loop(session, base_url):
	print()
	print(datetime.now())

	accounts = Accounts(session, base_url)
	cash, brokerage_account = accounts.cash_balance_from_account_AUTO()
	orders = AUTO_orders.main(cash, not triton_config.EXECUTE)

	if triton_config.EXECUTE:
		print("EXECUTE TRADES")
		for ticker, shares in orders:
			print(f"	Buy {shares} of {ticker}")

			order = Order(session, brokerage_account, base_url)
			order.place_market_order_AUTO(ticker, shares)

			#  exit plans, disabled currently due to day trading
			"""if response and response.status_code == 200:
				try:
					share_price = response['PlaceOrderResponse']/shares
					stop_loss = share_price * triton_config.MARKET_STOP_LOSS
					response = order.place_sell_limit_order_AUTO(ticker, shares, stop_loss)"""

	else:
		print("MOCK EXECUTE TRADES")
		for tick, shares in orders:
			print(f"	Mock buy {shares} of {tick}")


if __name__ == "__main__":
	oauth()
