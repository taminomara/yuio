import enum
import yuio.app
import yuio.io

class GreetingType(enum.Enum):  # [1]_
    FORMAL = "Formal"
    INFORMAL = "Informal"

@yuio.app.app
def main():
    name = yuio.io.ask("What's your name?")
    greeting_type = yuio.io.ask[GreetingType](  # [2]_
        "What kind of greeting do you want?",
        default=GreetingType.FORMAL,
    )

    if greeting_type is GreetingType.FORMAL:
        yuio.io.info("Hello, %s. I hope this email finds you well.", name)
    else:
        yuio.io.info("Hii %s! So good to see you!", name)

if __name__ == "__main__":
    main.run()
