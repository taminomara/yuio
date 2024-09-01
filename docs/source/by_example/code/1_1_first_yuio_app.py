import yuio.app

@yuio.app.app
def main(greeting: str = "world"):
    print(f"Hello, {greeting}!")

if __name__ == "__main__":
    main.run()
