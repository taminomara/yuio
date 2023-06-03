import enum

import yuio.io
import yuio.parse


class Dish(enum.Enum):
    FISH = 'fish'
    MEAT = 'meat'
    VEGAN_BURGER = 'vegan burger'


if __name__ == '__main__':
    food = yuio.io.ask('What would you like for dinner?', parser=Dish, default=Dish.VEGAN_BURGER)
    with_fries = yuio.io.ask_yn('Maybe add some fries?', default=True)

    yuio.io.info('Alright, %s it is!', food)
