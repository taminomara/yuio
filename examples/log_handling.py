import logging

import yuio.io

if __name__ == "__main__":
    logger = logging.getLogger("icq_hacking_tool_2000")
    logger.addHandler(yuio.io.Handler())
    logger.setLevel(logging.INFO)

    logger.info("Starting an application...")
    logger.info("Initializing ChatGPT...")
    logger.warning("ChatGPT is hacking Pentagon!")
    logger.critical("🚨 FBI open up!")
