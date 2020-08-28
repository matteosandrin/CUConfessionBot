from flask import Flask
from bot import CCTwitterBot

app = Flask(__name__)

@app.route('/update')
def update():
    bot = CCTwitterBot()
    bot.process()
    return 'The bot was updated!'

@app.route('/logs')
def logs():
    lines = CCTwitterBot.getLogs()
    html = lines.replace('\n', '<br>')
    html = '<span style="font-family: Monaco">{}</span>'.format(html)
    return html

if __name__ == "__main__":
    app.run()