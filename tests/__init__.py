import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("subclient").level = logging.DEBUG
logging.getLogger("moonbot").level = logging.DEBUG
