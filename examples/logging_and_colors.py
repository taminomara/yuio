import yuio.io

if __name__ == '__main__':
    yuio.io.setup(level=yuio.io.DEBUG)

    yuio.io.info('<c:b>Log level colors:</c>')
    yuio.io.info('')
    yuio.io.debug('Debug message is gray.')
    yuio.io.info('Info message is default color.')
    yuio.io.warning('Warning message is yellow.')
    yuio.io.error('Error message is red.')
    yuio.io.critical('Critical message is SCARY RED.')
    yuio.io.info('')
    yuio.io.info('')
    yuio.io.info('<c:b>Color tags:</c>')
    yuio.io.info('')
    yuio.io.info("This text is <c:red,bold>red!</c>")
    yuio.io.warning('File <c:code>example.txt</c> does not exist.')
