import logging

import yuio.io

if __name__ == "__main__":
    logger = logging.getLogger("icq_hacking_tool_2000")
    logger.addHandler(yuio.io.Handler())
    logger.setLevel(logging.DEBUG)

    logger.debug("Starting an application...")
    logger.info("Initializing ChatGPT...")
    logger.warning("ChatGPT sends fake crime notifications to FBI!")
    logger.error("We've been detected!")
    logger.critical("🚨 FBI open up!")
