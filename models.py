import threading
import urllib, urllib2
from BeautifulSoup import BeautifulSoup

# A Path Moment

class Moment():
    def __init__(self, id, text, path_url, user):
        self.id = id
        self.text = text
        self.path_url = path_url
        self.user = user
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
    
    def getTwitterHandle(self):
        return self.user

class GetHtmlFromUrlThread(threading.Thread):
    def __init__(self, moment_queue):
        threading.Thread.__init__(self)
        self.moment_queue = moment_queue

    def run(self):
        while True:
            moment = self.moment_queue.get()
            url = moment.getPathUrl()
            #print url
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
        pass

