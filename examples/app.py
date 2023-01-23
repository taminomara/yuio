import enum
import pathlib
from typing import *

import yuio.app
import yuio.config
import yuio.parse
import yuio.io


class Config(yuio.config.Config):
    """global configuration

    """

    #: number of threads to use for executing model
    threads: int = yuio.config.field(4, parser=yuio.parse.Int().ge(1))

    #: enable or disable gpu
    gpu: bool = True


CONFIG = Config()


@yuio.app.App
def main(config: Config):
    """some ml stuff idk im not into ml

    """

    config_file = pathlib.Path(__file__).parent / 'app_config.json'
    CONFIG.update(Config.load_from_json_file(config_file))
    CONFIG.update(Config.load_from_env('YUIO'))
    CONFIG.update(config)
    yuio.io.debug('global config is loaded: %s', CONFIG)


@main.subcommand
def run(
    #: trained model to execute
    model: pathlib.Path,

    #: input data for the model
    data: pathlib.Path
):
    """apply trained model to a dataset.

    """

    yuio.io.info('applying model <c:code>%s</c> to data <c:code>%s</c>', model, data)


@main.subcommand(aliases=['t'])
class Train(yuio.app.Command):
    """train model on a dataset.

    """

    #: input data for the model
    data: pathlib.Path = yuio.config.field(
        parser=yuio.parse.Path(extensions=['.bin']),
        flags=['-i', '--input'],
    )

    #: output data for the model
    output: Optional[pathlib.Path] = yuio.config.field(
        parser=yuio.parse.Path(extensions=['.model']),
        flags=['-o', '--output'],
        default=None,
    )

    class ModelStat(enum.Enum):
        LL = enum.auto()
        ROC = enum.auto()
        AUC = enum.auto()
        F1 = enum.auto()
        MAE = enum.auto()
        MSE = enum.auto()

    #: list of model statistics that needs to be exported
    stats: FrozenSet[ModelStat] = frozenset({ModelStat.MSE, ModelStat.AUC})

    def run(self):
        yuio.io.info('training model <c:code>%s</c> on data <c:code>%s</c>', self.output, self.data)


if __name__ == '__main__':
    main.run()
