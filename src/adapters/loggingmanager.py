import logging
import warnings

warnings.filterwarnings(action="ignore", message=".*Failed to resolve*")
warnings.filterwarnings(action="ignore", message=".*Failed to establish*")


def azure_logger():
    """
    Method to log messages.

    Returns:
        logger: Logger object
    """
    logging.basicConfig(
        filename="../5DayNltoSQL/logs.log",
        filemode="a",
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.INFO,
    )
    logger = logging.getLogger("AI AI Bot")
    logger.info("Logger Initialised..")
    return logger


logger = azure_logger()
