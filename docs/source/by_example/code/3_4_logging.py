import logging
import yuio.app

logger = logging.getLogger("main")

@yuio.app.app
def main(foo: str = "", bar: str = ""):
    logger.debug("settings: foo=%r, bar=%r", foo, bar)
    logger.info("Running some logic...")

if __name__ == "__main__":
    main.run()
