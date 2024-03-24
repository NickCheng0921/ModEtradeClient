from flask import Flask, jsonify

# hack needed in order to use local modules
import sys, os
sys.path.append(os.getcwd())

from apscheduler.schedulers.background import BackgroundScheduler
import CHARIOT
import datetime
import time

app = Flask(__name__)
session, base_url = CHARIOT.oauth()

@app.route('/', methods=['GET'])
def get_cash():
	cash = CHARIOT.get_cash_balance(session, base_url)
	if cash:
		return jsonify({'cash' : cash})
	return jsonify({})

def renew_session_token():
	today = datetime.now()
	print('\n', 'Token refresh at ', today.strftime('%Y-%m-%d | %H:%M:%S'), '\n')
	
	response = CHARIOT.renew_session(session)

	if response.status_code != 200:
		print(f"Refresh failed once, trying again in {CHARIOT.OAUTH_RETRY_MIN} minutes")
		time.sleep(CHARIOT.OAUTH_RETRY_MIN*60)
		response = CHARIOT.renew_session(session)
		if response.status_code != 200:
			print("Refresh failed twice")

scheduler = BackgroundScheduler()
scheduler.add_job(func=renew_session_token, trigger="interval", seconds=CHARIOT.OAUTH_REFRESH_MIN*60)
scheduler.start()

if __name__ == '__main__':
	app.run(debug=True, threaded=True)