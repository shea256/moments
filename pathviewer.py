from flask import Flask, request, render_template, send_from_directory
import json, urllib, urllib2
import string
from BeautifulSoup import BeautifulSoup
import Queue
import threading
import time
import os
from werkzeug.contrib.cache import SimpleCache
import pusher

cache = SimpleCache()

#pusher.app_id = '17452'
#pusher.key = '707a21bc6e05a8c64325'
#pusher.secret = 'a318e255b90c66fd82e4'
pusher.app_id = '17465'
pusher.key = '5b7cb63a557f941ee1aa'
pusher.secret = '80e7e4e4bc8cd488e802'

p = pusher.Pusher()

app = Flask(__name__)

app.config.update(
	DEBUG = False,
)

class TaskThread(threading.Thread):
    """Thread that executes a task every N seconds"""
    
    def __init__(self):
        threading.Thread.__init__(self)
        self._finished = threading.Event()
        self._interval = 15.0
    
    def setInterval(self, interval):
        """Set the number of seconds we sleep between excuting our task"""
        self._interval = interval
    
    def shutdown(self):
        """Stop this thread"""
        self._finished.set()
    
    def run(self):
        while True:
            if self._finished.isSet(): return
            self.task()
            
            # sleep for interval or until shutdown
            self._finished.wait(self._interval)
    
    def task(self):
        """The task done by this thread - override in subclasses"""
        #pass
        update_photo_moments_in_cache()

class GetHtmlFromUrlThread(threading.Thread):
    def __init__(self, moment_queue):
        threading.Thread.__init__(self)
        self.moment_queue = moment_queue

    def run(self):
        while True:
            moment = self.moment_queue.get()
            url = moment.getPathUrl()
            print url
            try:
                opened_url = urllib2.urlopen(url)
                try:
                    html = opened_url.read()
                    #self.html_queue.put(html)
                    try:
                        soup = BeautifulSoup(html)
                        photo_containers = soup.findAll("div", { "class" : "photo-container"})
                        if len(photo_containers) is 1:
                            photo_url = photo_containers[0].img['src']
                            #print photo_link
                            moment.setPhotoUrl(photo_url)
                            #print moment.getPhotoUrl()
                    except:
                        print "unable to parse html"
                except:
                    print "unable to read html"
            except:
                print "unable to open link"
            self.moment_queue.task_done()

class Moment():
    def __init__(self, id, text, path_url, from_user):
        self.id = id
        self.text = text
        self.path_url = path_url
        self.from_user = from_user
        self.photo_url = None
    
    def setPhotoUrl(self, photo_url):
        self.photo_url = photo_url
    
    def getPhotoUrl(self):
        return self.photo_url
    
    def getText(self):
        return self.text
    
    def getPathUrl(self):
        return self.path_url
    
    def getId(self):
        return self.id
    
    def getFromUser(self):
        return self.from_user

def get_tweet_results_from_search_url(search_url):
    resultsContainer = json.load(urllib.urlopen(search_url))
    tweet_results = resultsContainer['results']
    return tweet_results

def removeNonAscii(s):
    return "".join(i for i in s if ord(i)<128)

def get_photo_moments_from_tweet_results(tweet_results):
    moments = []
    for result in tweet_results:
        text = result['text']
        words = text.split()
        wordcount = len(words)
        if wordcount >= 3:
            if string.find(words[wordcount-3], "[pic]") >= 0:
                if string.find(words[wordcount-1], "http://") >= 0:
                    moment_id = result['id']
                    path_url = words[wordcount-1]
                    path_url = path_url.rstrip('\"')
                    path_url = removeNonAscii(path_url)
                    from_user = result['from_user']
                    moment = Moment(moment_id, text, path_url, from_user)
                    moments.append(moment)
    return moments

def add_photo_links_to_photo_moments(moments):
    number_urls = len(moments)
    
    moment_queue = Queue.Queue()
    
    for i in range(number_urls):
        html_thread = GetHtmlFromUrlThread(moment_queue)
        html_thread.setDaemon(True)
        try:
            html_thread.start()
        except:
            print "could not start thread"
    
    for moment in moments:
        moment_queue.put(moment)
    
    moment_queue.join()
    
    return moments

def get_current_photo_moments():
    # http://search.twitter.com/search.json?q=path.com%2Fp%2F
    SEARCH_BASE = 'http://search.twitter.com/search.json?q=path.com%2Fp%2F&result_type=recent'
    tweet_results = get_tweet_results_from_search_url(SEARCH_BASE)
    moments = get_photo_moments_from_tweet_results(tweet_results)
    
    #start = time.time()
    moments = add_photo_links_to_photo_moments(moments)
    #print "Elapsed Time: %s" % (time.time() - start)
    return moments

def update_photo_moments_in_cache():
    print "updating cache..."
    photo_moments = get_current_photo_moments()
    if len(photo_moments) > 0:
        photo_url = str(photo_moments[0].getPhotoUrl())
        photo_id = str(photo_moments[0].getId())
        path_url = str(photo_moments[0].getPathUrl())
        p['a_channel'].trigger('an_event', {'photo_url': photo_url, 'id':photo_id, 'path_url':path_url})
        cache.set('photo_moments', photo_moments, timeout=10)

def get_photo_moments_from_cache():
    photo_moments = cache.get('photo_moments')
    if photo_moments is None:
        print "updating cache..."
        photo_moments = get_current_photo_moments()
        cache.set('photo_moments', photo_moments, timeout=10)
    return photo_moments

@app.route('/')
def index():
    photo_moments = get_photo_moments_from_cache()
    return render_template('moment.html', photo_moments=photo_moments)

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

