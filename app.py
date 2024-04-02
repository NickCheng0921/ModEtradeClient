from flask import Flask, jsonify

# hack needed in order to use local modules
import sys, os
sys.path.append(os.getcwd())

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import CHARIOT
import datetime
import time

app = Flask(__name__)
oauth_lock = False

def renew_session_token():
	if oauth_lock:
		print("\nOAUTH locked, skipping renew cycle\n")

	today = datetime.now()
	print('\n', 'TOK Token refresh at ', today.strftime('%Y-%m-%d | %H:%M:%S'), '\n')
	
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
	print("\nTOK Access token generated\n")

	return session, base_url

session, base_url = renew_access_token()

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

if __name__ == '__main__':
	app.run(debug=True, threaded=True)