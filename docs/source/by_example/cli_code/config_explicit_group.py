import pathlib
import yuio.app

CONFIG_GROUP = yuio.app.HelpGroup("Config")

@yuio.app.app
def main(
    #: Override default path to config.
    config: pathlib.Path | None = yuio.app.field(
        default=None,
        help_group=CONFIG_GROUP,
    ),
    #: Print output in machine readable format.
    machine_readable: bool = yuio.app.field(
        default=False,
        help_group=yuio.app.MISC_GROUP,
    ),
):
    ...

if __name__ == "__main__":
    main.run()
