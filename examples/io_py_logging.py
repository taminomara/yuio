import logging

import yuio.io

if __name__ == '__main__':
    logger = logging.getLogger('my_application_logger')
    logger.addHandler(yuio.io.Handler())
    logger.setLevel(logging.INFO)

    logger.info('Starting an application...')
    logger.info('Initializing ChatGPT...')
    logger.warning('ChatGPT is hacking Pentagon!')
    try:
        import yuio.parse
        yuio.parse.Int().parse('asd')
    except:
        logger.exception('🚨 FBI open up!')
