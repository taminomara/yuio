import enum

import yuio.io


class Console(enum.Enum):
    GameBoy = "GameBoy"
    Wii = "Wii"
    PlayStation2 = "PlayStation2"
    PlayStationPortable = "PlayStationPortable"
    XboxOne = "XboxOne"
    Genesis = "MegaDrive/Genesis"
    Atari2600 = "Atari2600"


if __name__ == "__main__":
    consoles = yuio.io.ask[set[Console]]("Which consoles do you own?")
    if len(consoles) == len(Console):
        yuio.io.success("You have them all!")
    else:
        yuio.io.success("You have %s", yuio.io.And(consoles, fallback="...nothing?"))
