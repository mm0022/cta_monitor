import logging

from nexus_data_hub_sdk.share.settings import LOGGING_LEVEL

logger = logging.getLogger('data_hub_sdk')
if LOGGING_LEVEL.upper() in ('NOTSET', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'):
    logger.setLevel(LOGGING_LEVEL.upper())
else:
    logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)
