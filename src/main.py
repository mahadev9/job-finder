import logging

from src.logger import bootstrap_logging

bootstrap_logging()

logger = logging.getLogger("job-finder")
