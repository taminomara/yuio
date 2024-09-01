import yuio.app
import yuio.io
from time import sleep

@yuio.app.app
def main():
    with yuio.io.Task("Sending a greeting"):
        send_greeting()

def send_greeting():
    sleep(5)  # Sending greeting requires five seconds.

if __name__ == "__main__":
    main.run()
