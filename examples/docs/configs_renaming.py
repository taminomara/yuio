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
