from flask import Flask, jsonify, request

# hack needed in order to use local modules
# run with python -m flask run --host=0.0.0.0
import sys, os
sys.path.append(os.getcwd())

from order.order import Order
from accounts.accounts import Accounts

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import CHARIOT
from datetime import datetime
import time

app = Flask(__name__)
oauth_lock = False
session, base_url, brk_acc = None, None, None

def renew_session_token():
	if oauth_lock:
		print("\nOAUTH locked, skipping renew cycle\n")
		return

	today = datetime.now()
	print('\n', "TOK Session token refresh at ", today.strftime('%Y-%m-%d | %H:%M:%S'), '\n')
	
	response = CHARIOT.renew_session(session)

	if response.status_code != 200:
		print(f"Refresh failed once, trying again in {CHARIOT.OAUTH_RETRY_MIN} minutes")
		time.sleep(CHARIOT.OAUTH_RETRY_MIN*60)
		response = CHARIOT.renew_session(session)
		if response.status_code != 200:
			print("Refresh failed twice")

def renew_access_token():
	oauth_lock = True
	session, base_url = CHARIOT.oauth()
	oauth_lock = False

	accounts = Accounts(session, base_url)
	_, brk_acc = accounts.cash_balance_from_account_AUTO()

	today = datetime.now()
	print("\nTOK Access token generated at ", today.strftime('%Y-%m-%d | %H:%M:%S'), '\n')

renew_access_token()
accounts = Accounts(session, base_url)

scheduler = BackgroundScheduler()
scheduler.add_job(func=renew_session_token, trigger="interval", seconds=CHARIOT.OAUTH_REFRESH_MIN*60)
scheduler.add_job(func=renew_access_token, trigger=CronTrigger(hour=0, minute=0))
scheduler.start()

@app.route('/', methods=['GET'])
def get_cash():
	cash = CHARIOT.get_cash_balance(session, base_url)
	if cash:
		return jsonify({'cash' : cash})
	return jsonify({})

@app.route('/market', methods=['POST'])
def market():
	data = request.form
	ticker = data.get('ticker')
	shares = int(data.get('shares'))
	action = data.get('action')

	order = Order(session, brk_acc, base_url)
	call = order.place_market_order_AUTO(ticker, shares, action)
	return jsonify({}), call.status_code

@app.route('/buy_limit', methods=['POST'])
def buy_limit():
	data = request.form
	ticker = data.get('ticker')
	direction = data.get('direction')
	shares = int(data.get('shares'))
	stop = float(data.get('stop'))

	order = Order(session, brk_acc, base_url)
	call = order.place_limit_order_AUTO(ticker, shares, stop, direction)
	return jsonify({}), call.status_code

if __name__ == '__main__':
	app.run(debug=True, threaded=True)