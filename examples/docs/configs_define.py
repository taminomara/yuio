import yuio.config

class Config(yuio.config.Config):
    #: what kind of greeting does a user want?
    use_formal_greeting: bool = False

    #: who the greeting is coming from?
    sender_name: str | None = None
