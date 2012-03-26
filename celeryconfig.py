# List of modules to import when celery starts.
CELERY_IMPORTS = ("tasks", )

# Result store settings.
CELERY_RESULT_BACKEND = "sqlalchemy"
CELERY_RESULT_DBURI = "sqlite:///mydatabase.db"
BROKER_TRANSPORT = "sqlalchemy"
BROKER_HOST = "sqlite:///celerydb.sqlite"

# Broker settings.
#BROKER_URL = "amqp://guest@localhost:5000//"
#BROKER_HOST = "localhost"
#BROKER_PORT = 5672
#BROKER_USER = "myuser"
#BROKER_PASSWORD = "mypassword"

BROKER_VHOST = "myvhost"






