import enum
import pathlib
from typing import *

import yuio.config
import yuio.io
import yuio.parse


class ExecutorConfig(yuio.config.Config):
    #: number of threads to use for executing model
    threads: int = yuio.config.field(
        default=4,
        parser=yuio.parse.Bound(yuio.parse.Int(), lower_inclusive=1),
        flags=['-t', '--threads']
    )

    #: enable or disable gpu
    use_gpu: bool = yuio.config.field(
        default=True,
        flags=['--gpu']
    )


class ModelStat(enum.Enum):
    LL = enum.auto()
    ROC = enum.auto()
    AUC = enum.auto()
    F1 = enum.auto()
    MAE = enum.auto()
    MSE = enum.auto()


class AppConfig(yuio.config.Config):
    #: trained model to execute
    model: pathlib.Path = yuio.config.field(
        parser=yuio.parse.Path(extensions=['.model']),
        flags=['-m', '--model'],
        required=True,
    )

    #: input data for the model
    data: pathlib.Path = yuio.config.field(
        parser=yuio.parse.Path(extensions=['.bin']),
        flags=['-i', '--input'],
        required=True,
    )

    #: executor arguments
    #:
    #: arguments that control executor backend and how it interacts
    #: with hardware
    executor: ExecutorConfig = yuio.config.field(
        flags='',  # Disable prefixing executor flags with `--executor-...`
    )

    #: list of model statistics that needs to be exported
    stats: FrozenSet[ModelStat] = frozenset({ModelStat.MSE, ModelStat.AUC})


if __name__ == '__main__':
    config_file = pathlib.Path(__file__).parent / 'config.json'

    config = AppConfig.load_from_json_file(config_file)
    config.update(AppConfig.load_from_env('YUIO'))
    config.update(AppConfig.load_from_args())

    yuio.io.info(f'{config!r}')
