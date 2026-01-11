import yuio.app

@yuio.app.app()  # [1]_
def main(
    greeting: str = "world",  # [2]_
):
    print(f"Hello, {greeting}!")

if __name__ == "__main__":
    main.run()  # [3]_
