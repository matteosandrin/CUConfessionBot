from flask import Flask
from bot import CCTwitterBot
import threading

app = Flask(__name__)

@app.route('/update')
def update():
    bot = CCTwitterBot()
    thread = threading.Thread(target=bot.process)
    thread.start()
    return 'Bot is updating!'

@app.route('/logs')
def logs():
    lines = CCTwitterBot.getLogs()
    html = lines.replace('\n', '<br>')
    html = '<span style="font-family: Monaco">{}</span>'.format(html)
    return html

if __name__ == "__main__":
    app.run()