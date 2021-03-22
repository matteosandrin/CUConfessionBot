from flask import Flask
from bot import CCTwitterBot
import arrow
import os.path
import json

app = Flask(__name__)
EXPIRY_FILE = CCTwitterBot.absolutePath('expiry.json')
LOGS_TEMPLATE = open(CCTwitterBot.absolutePath('templates/logs.html')).read()

@app.route('/update')
def update():
    bot = CCTwitterBot()
    bot.process()
    if isExpired():
        updateLastExpiryDate()
        bot.notifyOwner('Please update me on https://www.pythonanywhere.com/. I will expire in a few days otherwise!')
    return 'The bot was updated!'

@app.route('/logs')
def logs():
    lines = CCTwitterBot.getLogs()
    html_lines = lines.replace('\n', '<br>')
    html = LOGS_TEMPLATE.replace('INSERT_LOGS_HERE', html_lines)
    return html

def isExpired():
    if not os.path.exists(EXPIRY_FILE):
        updateLastExpiryDate()
        return True
    data = json.load(open(EXPIRY_FILE))
    lastExpiryUTC = data['lastExpiryUTC']
    diff = arrow.utcnow() - arrow.get(lastExpiryUTC)
    return diff.days > 89

def updateLastExpiryDate():
    now = arrow.utcnow()
    data = { 'lastExpiryUTC' : now.timestamp }
    f = open(EXPIRY_FILE, 'w')
    f.write(json.dumps(data))
    f.close()

if __name__ == "__main__":
    app.run()