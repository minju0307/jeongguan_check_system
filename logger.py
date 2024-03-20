import logging
from logging.config import dictConfig

from config import DEBUG

dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s (%(module)s:%(lineno)d) %(name)s - %(levelname)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'web_server.log',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'file']
    },
    'loggers': {
        'waitress': {
            'level': 'INFO'
        }
    }
})

logger = logging.getLogger('web_server')  # flask app logger와 동일한 이름으로 설정

if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
