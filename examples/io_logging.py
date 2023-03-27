import yuio.io

if __name__ == '__main__':
    yuio.io.setup(level=yuio.io.LogLevel.DEBUG)

    yuio.io.info('<c:heading>Log level colors:</c>')
    yuio.io.debug('  Debug message is gray.')
    yuio.io.info('  Info message is default color.')
    yuio.io.warning('  Warning message is yellow.')
    yuio.io.error('  Error message is red.')
    yuio.io.critical('  Critical message is SCARY RED. Boo!')
    yuio.io.info('<c:heading>Color tags:</c>')
    yuio.io.info('  This text is <c:red,bold>red!</c>')
    yuio.io.warning('  File <c:code>example.txt</c> does not exist.')
