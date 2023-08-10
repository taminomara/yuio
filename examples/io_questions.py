import enum

import yuio.io
import yuio.parse


class Dish(enum.Enum):
    FISH = 'fish'
    MEAT = 'meat'
    VEGAN_BURGER = 'vegan burger'


if __name__ == '__main__':
    dish = yuio.io.ask[Dish]('What would you like for dinner?', default=Dish.VEGAN_BURGER)
    with_fries = yuio.io.ask_yn('Maybe add some fries?', default=True)

    description = dish.value
    if with_fries:
        description += ' with fries'

    yuio.io.info('Alright, %s it is!', description)
