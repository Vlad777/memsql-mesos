import logging
import logging.handlers
import logging.config

def setup():
    format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "machine": {
                "format": format_string
            },
            "human": {
                "format": format_string
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "human",
                "level": "INFO"
            }
        },
        "root": {
            "handlers": [ "console" ],
            "level": "DEBUG"
        },
        "loggers": {
            "tornado": {
                "level": "WARN"
            },
            "requests": {
                "level": "WARN"
            },
            "urllib3": {
                "level": "WARN"
            }

        }
    })
