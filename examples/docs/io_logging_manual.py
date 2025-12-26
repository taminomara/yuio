import logging
import yuio.app
import yuio.io

logger = logging.getLogger("main")

@yuio.app.app
def main(foo: str = "", bar: str = ""):
    logging.basicConfig(
        level=logging.INFO,
        handlers=[yuio.io.Handler()],
    )

    logger.debug("settings: foo=%r, bar=%r", foo, bar)
    logger.info("Running some logic...")

main.setup_logging = False

if __name__ == "__main__":
    main.run()
