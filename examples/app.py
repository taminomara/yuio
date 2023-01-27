import pathlib

import yuio.app
import yuio.config
import yuio.parse
import yuio.io


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
def main(_subcommand, config: Config = yuio.config.inline()):
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

    yuio.io.debug('global config is loaded: %s', CONFIG)


@main.subcommand(aliases=['r'])
def run(
    #: trained model to execute
    model: pathlib.Path,
    #: input data for the model
    data: pathlib.Path,
):
    """apply trained model to a dataset.

    """

    yuio.io.info('applying model <c:code>%s</c> to data <c:code>%s</c>', model, data)


@main.subcommand(aliases=['t'])
def train(
    #: input data for the model
    data: pathlib.Path,
    #: output data for the model
    output: pathlib.Path = pathlib.Path('trained.bin'),
):
    """train model on a dataset.

    """

    yuio.io.info('training model <c:code>%s</c> on data <c:code>%s</c>', output, data)


if __name__ == '__main__':
    main.run()
