import dataclasses
import yuio.app
import yuio.io

@dataclasses.dataclass
class CoordinateSystem:
    origin: tuple[int, int] = (0, 0)
    scale: tuple[float, float] = (1.0, 1.0)

@yuio.app.app
def main():
    coordinates = CoordinateSystem()
    yuio.io.info("Main coordinate system: %#+r", coordinates)

if __name__ == "__main__":
    main.run()
