import pathlib

import yuio.app
import yuio.config
import yuio.io
import yuio.parse


class Config(yuio.config.Config):
    """global configuration

    global options are loaded from `app_config.json`,
    from environment variables, and from CLI arguments.

    """

    #: number of threads to use for executing model
    threads: int = yuio.config.field(4, parser=yuio.parse.Int().ge(1))

    #: enable or disable gpu
    gpu: bool = True


# We will load values into this variable once the program starts.
CONFIG = Config()


@yuio.app.app
def main(config: Config = yuio.config.inline()):
    """some ml stuff idk im not into ml

    """

    # Load global config:

    # From file...
    config_file = pathlib.Path(__file__).parent / 'app_config.json'
    CONFIG.update(Config.load_from_json_file(config_file))

    # From environment variables...
    CONFIG.update(Config.load_from_env('YUIO'))

    # From CLI arguments...
    CONFIG.update(config)

    yuio.io.info('global config is loaded: <c:code>%r</c>', CONFIG)


main.epilog = """
usage examples:
  app.py train training.bin\v
  app.py run trained.model sample.bin\v

note:
  yuio splits text into paragraphs and fills them according to available
  terminal width. This means that original line breaks are ignored.
  When it's not desirable, use `\\v` at the end of line to indicate that
  this particular linebreak should be preserved.

"""


@main.subcommand(aliases=['r'])
def run(
    #: trained model to execute
    model: pathlib.Path = yuio.config.positional(),
    #: input data for the model
    data: pathlib.Path = yuio.config.positional(),
):
    """apply trained model to a dataset.

    """

    yuio.io.info('applying model <c:code>%s</c> to data <c:code>%s</c>', model, data)


@main.subcommand(aliases=['t'])
def train(
    #: input data for the model
    data: pathlib.Path = yuio.config.positional(),

    #: output data for the model
    output: pathlib.Path = yuio.config.field(
        default=pathlib.Path('trained.model'),
        flags=['-o', '--out', '--output'],
    ),

    foo_bar: tuple[int, str] = (0, ''),
):
    """train model on a dataset.

    """

    yuio.io.info('training model <c:code>%s</c> on data <c:code>%s</c>', output, data)


if __name__ == '__main__':
    main.run()
