import logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(name)s | %(module)s | %(funcName)s | %(levelname)s | %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": logging.INFO,
        },
    },
    "loggers": {
        "job-finder": {
            "handlers": ["console"],
            "level": logging.INFO,
            "propagate": False,
        },
        "reflex": {
            "handlers": ["console"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": logging.WARNING,
            "propagate": False,
        },
    },
}


def bootstrap_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
