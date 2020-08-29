import facebook_scraper as fb
import json
import os
import re
import tweepy
import io
import time
import dotenv
from typing import List
from weasyprint import HTML, CSS
from datetime import datetime

class CCTwitterBot:

    def __init__(self):
        self.pageName = 'columbiaconfessionz'
        self.template = open(CCTwitterBot.absolutePath('template.html')).read()
        self.loadState()
        self.setupApi()

    @staticmethod
    def absolutePath(path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    @staticmethod
    def log(text, isError=False):
        logFile = open(CCTwitterBot.absolutePath('bot.log'), 'a')
        if isError:
            print('[!] ' + text, file=logFile)
        else:
            print('[+] ' + text, file=logFile)
        logFile.close()

    @staticmethod
    def getLogs():
        path = CCTwitterBot.absolutePath('bot.log')
        if not os.path.exists(path):
            return ''
        logFile = open(path, 'r')
        return logFile.read()

    def setupApi(self):
        """Load credentials from .env file and setup Twitter API"""
        dotenv.load_dotenv(CCTwitterBot.absolutePath('.env'))

        consumer_key = os.getenv('CONSUMER_KEY')
        consumer_secret = os.getenv('CONSUMER_SECRET')
        access_token = os.getenv('ACCESS_TOKEN')
        access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')

        if (consumer_key is None) or (len(consumer_key) == 0):
            CCTwitterBot.log('The consumer_key is missing from the ".env" file', isError=True)
            self.api = None
            return
        if (consumer_secret is None) or (len(consumer_secret) == 0):
            CCTwitterBot.log('The consumer_secret is missing from the ".env" file', isError=True)
            self.api = None
            return
        if (access_token is None) or (len(access_token) == 0):
            CCTwitterBot.log('The access_token is missing from the ".env" file', isError=True)
            self.api = None
            return
        if (access_token_secret is None) or (len(access_token_secret) == 0):
            CCTwitterBot.log('The access_token_secret is missing from the ".env" file', isError=True)
            self.api = None
            return

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    def loadState(self, path: str = None):
        """
        Load the state of the bot from disk.
        If there is no path, use the default path ('./state.json') 
        If there is no state, create the initial state
        """
        if path is None:
            path = CCTwitterBot.absolutePath('state.json')
        if not os.path.exists(path):
            self.state = set()
            self.dumpState()
        stateFile = open(path, 'r')
        rawState = json.load(stateFile)
        self.state = set(rawState['published'])

    def dumpState(self, path: str = None):
        """
        Write the state of the bot to disk.
        If there is no path, use the default path ('./state.json') 
        """
        if path is None:
            path = CCTwitterBot.absolutePath('state.json')
        stateFile = open(path, 'w')
        rawState = { 'published' : [h for h in self.state] }
        json.dump(rawState, stateFile)
        stateFile.close()

    def updateState(self, post: dict):
        """Add a new post id to the current state, and write it to disk"""
        idNum = post['post_id']
        self.state.add(idNum)
        self.dumpState()

    def getNewPosts(self):
        """Scrape the Facebook page for new posts, and filter out previously seen posts"""
        CCTwitterBot.log('Retrieving new posts')
        posts = fb.get_posts(self.pageName, pages=5)
        posts = [p for p in posts if p['post_id'] not in self.state]
        CCTwitterBot.log('Successfully retrieved {} new posts'.format(len(posts)))
        return posts

    def isConfession(self, post):
        """Returns True if the post is a confession"""
        text = post['text']
        matches = list(re.finditer(r'([\r\n]+|^)(\d{4,7})(\.)', text))
        return len(matches) > 0

    def deEmojify(self, text):
        regrex_pattern = re.compile(pattern = "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002500-\U00002BEF"  # chinese char
            u"\U00002702-\U000027B0"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001f926-\U0001f937"
            u"\U00010000-\U0010ffff"
            u"\u2640-\u2642"
            u"\u2600-\u2B55"
            u"\u200d"
            u"\u23cf"
            u"\u23e9"
            u"\u231a"
            u"\ufe0f"  # dingbats
            u"\u3030"
            "]+", flags = re.UNICODE)
        return regrex_pattern.sub(r'',text)

    def convertToImg(self, confession: str):
        """Render the confession text into an HTML page and convert it to a PNG image"""
        text = confession.replace('\n', '<br>')
        htmlStr = self.template.replace('INSERT_TEXT_HERE', text)
        
        css = CSS(string='@page { width: 664px; margin: 0px; padding: 0px }')
        html = HTML(string=htmlStr).render(stylesheets=[css])
        for page in html.pages:
            for child in page._page_box.descendants():
                if child.element_tag == 'body':
                    page._page_box.height = child.height
                    page.height = child.height
        imgBytes, _ , _ = html.write_png(None, resolution=150)
        return io.BytesIO(imgBytes)  

    def tweetImg(self, imgFile, post):
        """Tweet an image with the Twitter API"""
        CCTwitterBot.log('Sending tweet')
        self.api.update_with_media(CCTwitterBot.absolutePath('test.png'), post['post_url'], file=imgFile, )
        CCTwitterBot.log('Successuflly sent tweet')

    def process(self):
        CCTwitterBot.log('Starting at {}'.format(datetime.now().isoformat()))
        try:
            newPosts = self.getNewPosts()
        except:
            CCTwitterBot.log('ERROR: Failed to retrieve new posts', isError=True)
            return
        if self.api is None:
            CCTwitterBot.log('ERROR: The API is not setup correctly', isError=True)
            return
        for post in newPosts[::-1]:
            try:
                if self.isConfession(post):
                    text = self.deEmojify(post['text'])
                    imgFile = self.convertToImg(text)
                    self.tweetImg(imgFile, post)
                    time.sleep(0.5)
                self.updateState(post)
            except:
                CCTwitterBot.log('ERROR: Failed to send tweet', isError=True)
                break

if __name__ == "__main__":
    bot = CCTwitterBot()
    bot.process()