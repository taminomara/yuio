import yuio.config

class Config(yuio.config.Config):
    plugins: list[str] = yuio.config.field(
        default=[],
        merge=lambda left, right: [*left, *right],
    )
