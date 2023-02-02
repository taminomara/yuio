import yuio.io
import yuio.parse

if __name__ == '__main__':
    food = yuio.io.ask(
        'What would you like for dinner?',
        parser=yuio.parse.OneOf(
            yuio.parse.Str().lower(), ['fish', 'meet', 'vegan burger']
        ),
        default='vegan burger'
    )

    if yuio.io.ask_yn('Maybe add some fries?', default=True):
        food += ' with fries'

    yuio.io.info('Alright, %s it is!', food)
