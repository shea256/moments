from flask import Flask, request, render_template, send_from_directory
import json, urllib, urllib2
import string
from bs4 import BeautifulSoup
import Queue
import threading
import time
import os
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()

app = Flask(__name__)

app.config.update(
	DEBUG = True,
)

class GetHtmlFromUrlThread(threading.Thread):
    def __init__(self, url_queue, html_queue):
        threading.Thread.__init__(self)
        self.url_queue = url_queue
        self.html_queue = html_queue

    def run(self):
        while True:
            url = self.url_queue.get()
            try:
                opened_url = urllib2.urlopen(url)
                try:
                    html = opened_url.read()
                    self.html_queue.put(html)
                except:
                    print "unable to read html"
            except:
                print "unable to open link"
            self.url_queue.task_done()

class GetPhotoLinkFromHtmlThread(threading.Thread):
    def __init__(self, html_queue, photo_link_list):
        threading.Thread.__init__(self)
        self.html_queue = html_queue
        self.photo_link_list = photo_link_list
    
    def run(self):
        while True:
            html = self.html_queue.get()
            soup = BeautifulSoup(html)
            photo_containers = soup.findAll("div", { "class" : "photo-container"})
            if len(photo_containers) is 1:
                photo_link = photo_containers[0].img['src']
                print photo_link
                self.photo_link_list.append(photo_link)
            self.html_queue.task_done()

class TaskThread(threading.Thread):
    """Thread that executes a task every N seconds"""
    
    def __init__(self):
        threading.Thread.__init__(self)
        self._finished = threading.event()
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
        pass


def get_tweet_results_from_search_url(search_url):
    resultsContainer = json.load(urllib.urlopen(search_url))
    tweet_results = resultsContainer['results']
    return tweet_results

def get_path_urls_from_tweet_results(tweet_results):
    links = []
    for result in tweet_results:
        text = result['text']
        words = text.split()
        wordcount = len(words)
        if wordcount >= 3:
            if string.find(words[wordcount-3], "[pic]") >= 0:
                if string.find(words[wordcount-1], "http://") >= 0:
                    links.append(words[wordcount-1])
    return links

def get_photo_links_from_path_urls(path_urls):
    number_urls = len(path_urls)
    
    url_queue = Queue.Queue()
    html_queue = Queue.Queue()
    photo_url_list = []
    
    for i in range(number_urls):
        html_thread = GetHtmlFromUrlThread(url_queue, html_queue)
        html_thread.setDaemon(True)
        html_thread.start()
    
    for path_url in path_urls:
        url_queue.put(path_url)
    
    for i in range(number_urls):
        photo_link_thread = GetPhotoLinkFromHtmlThread(html_queue, photo_url_list)
        photo_link_thread.setDaemon(True)
        photo_link_thread.start()
    
    url_queue.join()
    html_queue.join()
    
    return photo_url_list


def get_current_tweets_and_photos():
    SEARCH_BASE = 'http://search.twitter.com/search.json?q=path.com%2Fp%2F'
    tweet_results = get_tweet_results_from_search_url(SEARCH_BASE)
    path_urls = get_path_urls_from_tweet_results(tweet_results)
    
    start = time.time()
    photo_links = get_photo_links_from_path_urls(path_urls)
    print "Elapsed Time: %s" % (time.time() - start)
    return {'tweet_results':tweet_results, 'photo_links':photo_links}

def get_tweets_and_photos_from_cache():
    tweet_results = cache.get('tweet_results')
    photo_links = cache.get('photo_links')
    if tweet_results is None or photo_links is None:
        results = get_current_tweets_and_photos()
        cache.set('tweet_results', results['tweet_results'], timeout=10)
        cache.set('photo_links', results['photo_links'], timeout=10)
        return results
    else:
        return {'tweet_results':tweet_results, 'photo_links':photo_links}

@app.route('/')
def index():
    result = get_tweets_and_photos_from_cache()
    tweet_results = result['tweet_results']
    photo_links = result['photo_links']
    #print tweet_results
    return render_template('moment.html', moments=tweet_results, photo_links=photo_links)

# http://search.twitter.com/search.json?q=path.com%2Fp%2F

#def main():
#    pass

if __name__ == '__main__':
    #main()
    # Bind to PORT if defined, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

