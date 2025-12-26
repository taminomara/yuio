import yuio.config

class Config(yuio.config.Config):
    use_formal_greeting: bool = yuio.config.field(
        default=False,
        flags=yuio.DISABLED,
        env=yuio.DISABLED,
    )

    ...
