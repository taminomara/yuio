import yuio.app
import yuio.io
from time import sleep

@yuio.app.app
def main():
    emails = ["a@example.com", "b@example.com", "c@example.com"]

    with yuio.io.Task("Sending greetings") as task:
        for i, email in enumerate(emails):
            task.comment(email)
            task.progress(i, len(emails))  # [1]_

            send_greeting()

def send_greeting():
    sleep(3)

if __name__ == "__main__":
    main.run()
