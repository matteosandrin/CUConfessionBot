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
        self.absolutePath = lambda local: os.path.join(os.path.dirname(os.path.realpath(__file__)), local)
        self.template = open(self.absolutePath('template.html')).read()
        self.loadState()
        self.setupApi()

    def log(self, text, isError=False):
        if isError:
            print('[!] ' + text)
        else:
            print('[+] ' + text)

    def setupApi(self):
        """Load credentials from .env file and setup Twitter API"""
        dotenv.load_dotenv(self.absolutePath('.env'))

        consumer_key = os.getenv('CONSUMER_KEY')
        consumer_secret = os.getenv('CONSUMER_SECRET')
        access_token = os.getenv('ACCESS_TOKEN')
        access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')

        if (consumer_key is None) or (len(consumer_key) == 0):
            self.log('The consumer_key is missing from the ".env" file', isError=True)
            self.api = None
            return
        if (consumer_secret is None) or (len(consumer_secret) == 0):
            self.log('The consumer_secret is missing from the ".env" file', isError=True)
            self.api = None
            return
        if (access_token is None) or (len(access_token) == 0):
            self.log('The access_token is missing from the ".env" file', isError=True)
            self.api = None
            return
        if (access_token_secret is None) or (len(access_token_secret) == 0):
            self.log('The access_token_secret is missing from the ".env" file', isError=True)
            self.api = None
            return

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)

    def loadState(self, path: str = None):
        """
        Load the state of the bot from disk.
        If there is no path, use the default path ('./state.json') 
        If there is no state, create the initial state
        """
        if path is None:
            path = self.absolutePath('state.json')
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
            path = self.absolutePath('state.json')
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
        self.log('Retrieving new posts')
        posts = fb.get_posts(self.pageName, pages=5)
        posts = [p for p in posts if p['post_id'] not in self.state]
        self.log('Successfully retrieved {} new posts'.format(len(posts)))
        return posts

    def isConfession(self, post):
        """Returns True if the post is a confession"""
        text = post['text']
        matches = list(re.finditer(r'([\r\n]+|^)(\d{4,7})(\.)', text))
        return len(matches) > 0

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
        self.log('Sending tweet')
        self.api.update_with_media(self.absolutePath('test.png'), post['post_url'], file=imgFile)
        self.log('Successuflly sent tweet')


    def process(self):
        self.log('Starting at {}'.format(datetime.now().isoformat()))
        try:
            newPosts = self.getNewPosts()
        except:
            self.log('ERROR: Failed to retrieve new posts', isError=True)
            return
        if self.api is None:
            self.log('ERROR: The API is not setup correctly', isError=True)
            return
        for post in newPosts[::-1]:
            try:
                if self.isConfession(post):
                    imgFile = self.convertToImg(post['text'])
                    self.tweetImg(imgFile, post)
                    time.sleep(1)
                self.updateState(post)
            except:
                self.log('ERROR: Failed to send tweet', isError=True)
                break

bot = CCTwitterBot()
bot.process()