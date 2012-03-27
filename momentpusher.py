from pathviewer import *

def runRefresher():
    #print "latest photo:" + latest_photo_url
    #p['a_channel'].trigger('an_event', {'photo_url': latest_photo_url})
    t = TaskThread()
    t.setInterval(10)
    t.run()

def main():
	runRefresher()

if __name__ == '__main__':
	main()