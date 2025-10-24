import yuio.app
import yuio.config

class Config(yuio.config.Config):
    use_formal_greeting: bool = yuio.config.field(
        default=False,
        flags=["-f", "--formal"],
        env="FORMAL",
    )

    sender_name: str | None = yuio.config.field(
        default=None,
        flags=["-s", "--sender"],
        env="SENDER",
    )

@yuio.app.app
def main(cli_config: Config = yuio.app.inline()):
    ...

    # `config.sender_name` will be loaded from `GREET_SENDER`.
    config = Config.load_from_env(prefix="GREET")

    ...

    _config = config

if __name__ == "__main__":
    main.run()
