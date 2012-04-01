from flask import Flask, request, render_template, send_from_directory
import json
import string
import Queue
import threading
import time
import os
from werkzeug.contrib.cache import SimpleCache
import pusher
import sys

import urllib, urllib2
from BeautifulSoup import BeautifulSoup

from time import sleep
from collections import deque

from models import *

#-----------------
# initialize app
#-----------------

app = Flask(__name__)

app.config.update(
    DEBUG = True,
)

#-----------------
# set up pusher
#-----------------

pusher.app_id = '17465'
pusher.key = '5b7cb63a557f941ee1aa'
pusher.secret = '80e7e4e4bc8cd488e802'
channel_name = 'a_channel'

p = pusher.Pusher()

#-----------------
# data storage
#-----------------

dispatch_queue = deque()
archive_queue = deque()
ARCHIVE_CAPACITY = 30
TIME_TO_CHECK_FOR_NEW_TWEETS = 10

#-----------------
# helper functions
#-----------------

def get_tweet_results_from_search_url(search_url):
    resultsContainer = json.load(urllib.urlopen(search_url))
    tweet_results = resultsContainer['results']
    new_search_params = resultsContainer['next_page']
    return (tweet_results, new_search_params)

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
                    user = result['from_user']
                    moment = Moment(moment_id, text, path_url, user)
                    moments.append(moment)
    return moments

def get_photo_moments_from_search_base(SEARCH_BASE, new_search_params, MAX_MOMENTS_TO_RETURN):
    MAX_MOMENTS_IN_ONE_PAGE = 10
    moments = []
    # loop until len(moments) hits a previously seen moment or reaches the maximum amount to return
    page_number = 1
    while (len(moments) < (MAX_MOMENTS_TO_RETURN - MAX_MOMENTS_IN_ONE_PAGE)):
        search_url = SEARCH_BASE + new_search_params
        # DONE --- CHANGE_6: use twitter next and previous page
        print "searching:" + search_url
        current_page_tweet_results, new_search_params = \
            get_tweet_results_from_search_url(search_url)
        current_page_moments = get_photo_moments_from_tweet_results(
            current_page_tweet_results)
        page_number += 1
        if len(archive_queue) > 0:
            latest_moment_in_archive_id = archive_queue[-1].getId()
            for i in range(len(current_page_moments)):
                if current_page_moments[i].getId() is latest_moment_in_archive_id:
                    moments.extend(current_page_moments[0:i])
                    return moments
        moments.extend(current_page_moments)
        # DONE --- CHANGE_5: stop when latest moment in queue is found in search
    return moments
    # returns moments in order of left to right, most recent to least recent

def add_photo_links_to_photo_moments(moments):
    NUMBER_OF_THREADS = 5
    moment_queue = Queue.Queue()
    
    for i in range(len(moments)):
        html_thread = GetHtmlFromUrlThread(moment_queue)
        html_thread.setDaemon(True)
        try:
            html_thread.start()
        except:
            print "could not start thread"
            sys.exit()
    
    for moment in moments:
        moment_queue.put(moment)
        
    moment_queue.join()
    
    return moments

# DONE --- CHANGE_6: get_html_from_url - use blocking queue again?

def get_recently_added_photo_moments():
    SEARCH_BASE = 'http://search.twitter.com/search.json'
    SEARCH_PARAMS = '?q=path.com%2Fp%2F'
    MAX_MOMENTS_TO_RETURN = ARCHIVE_CAPACITY
    moments = get_photo_moments_from_search_base(SEARCH_BASE, SEARCH_PARAMS, MAX_MOMENTS_TO_RETURN)
    #tweet_results = get_tweet_results_from_search_base(SEARCH_BASE)
    #moments = get_photo_moments_from_tweet_results(tweet_results)
    moments = add_photo_links_to_photo_moments(moments)
    return moments

def check_for_new_moments_and_update_store():
    moments = get_recently_added_photo_moments()
    moments = list(reversed(moments))
    if len(moments) > 0:
        # add moments to dispatch queue
        dispatch_queue.extendleft(moments)
        # add moments to archive queue
        print "\nArchive Queue Before ---"
        for moment in archive_queue:
            print moment.getTwitterHandle()
        archive_queue.extendleft(moments)
        print "Archive Queue After ---"
        for moment in archive_queue:
            print moment.getTwitterHandle()
        print "\n"
        # pop moments off of archive queue until it is the specified length
        while len(archive_queue) > ARCHIVE_CAPACITY:
            archive_queue.pop()

def run_data_mining_worker():
    class DataMiningThread(TaskThread):
        def task(self):
            check_for_new_moments_and_update_store()
    
    # every n seconds:
    while True:
        t = DataMiningThread()
        t.setInterval(TIME_TO_CHECK_FOR_NEW_TWEETS)
        t.run()
        #sleep(TIME_TO_CHECK_FOR_NEW_TWEETS) # DONE --- CHANGE_1 remove this and replace with a threading chron job

def run_dispatch_worker():
    while True:
        # every 100/n seconds
        seconds_to_sleep = 100.0/len(dispatch_queue)
        sleep(seconds_to_sleep)
        # get a moment (m) from the dispatch queue
        m = dispatch_queue.pop()
        # push the moment data to the client
        data = {'photo_url':m.getPhotoUrl(), 'id':m.getId(), 'path_url':m.getPathUrl(), 'text':m.getText(), 'twitter_handle':m.getTwitterHandle()}
        p[channel_name].trigger('new_moment', data) # DONE --- CHANGE_2: rename 'an_event' to 'send_moment' on server and client

#----------------------------------------
# app controllers, routing, and rendering
#----------------------------------------

def get_photo_moments_from_cache():
    #photo_moments = cache.get('photo_moments')
    #if photo_moment is None:
    #    pass
    #return photo_moments
    return list(archive_queue)

@app.route('/')
def index():
    photo_moments = get_photo_moments_from_cache()
    return render_template('moment.html', photo_moments=photo_moments)

#-----------------
# run the app
#-----------------

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    run_data_mining_worker()


