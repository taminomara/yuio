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
    yuio.io.info("You own `%s`", ", ".join(map(str, consoles)) or "...nothing?")
