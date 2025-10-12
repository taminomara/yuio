import yuio.app
import yuio.config
import yuio.parse

class Config(yuio.config.Config):
    #: what kind of greeting does a user want?
    use_formal_greeting: bool = False

    #: who the greeting is coming from?
    sender_name: str | None = None

    def validate_config(self):
        if self.sender_name == "guest":
            raise yuio.parse.ParsingError(
                f"sending greetings from {self.sender_name} is not allowed"
            )

@yuio.app.app
def main(cli_config: Config = yuio.app.inline()):
    config = Config()
    config.update(Config.load_from_json_file(
        "~/.greet_cfg.json", ignore_missing_file=True
    ))
    config.update(Config.load_from_env(prefix="GREET"))
    config.update(cli_config)

    ...

if __name__ == "__main__":
    main.run()
