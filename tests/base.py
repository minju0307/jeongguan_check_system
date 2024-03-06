import logging


class BaseTest():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s (%(module)s:%(lineno)d) %(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
