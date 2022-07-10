import time

import yuio

if __name__ == '__main__':
    yuio.io.setup()

    with yuio.io.Task('Preparing your dinner') as task:
        time.sleep(5)

        food = yuio.io.ask(
            'Actually... what would you like for dinner?',
            parser=yuio.parse.OneOf(
                yuio.parse.Str().lower(), ['fish', 'meet', 'vegan burger']
            ),
            default='vegan burger'
        )

        yuio.io.info('Alright, %s it is!', food)
        task.comment(food)
        time.sleep(10)

    yuio.io.info('<c:success>Your %s is ready!</c>', food)
