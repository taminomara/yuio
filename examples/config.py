import enum
import pathlib

import yuio


class ExecutorConfig(yuio.config.Config):
    threads: int = yuio.config.field(
        default=4,
        parser=yuio.parse.Bound(yuio.parse.Int(), lower_inclusive=1),
        help='number of threads to use for executing model',
        flags=['-t', '--threads']
    )

    use_gpu: bool = yuio.config.field(
        default=True,
        help='enable or disable gpu (default is enable)',
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
    model: pathlib.Path = yuio.config.field(
        parser=yuio.parse.Path(extensions=['.model']),
        help='trained model to execute',
        flags=['-m', '--model'],
        required=True,
    )

    data: pathlib.Path = yuio.config.field(
        parser=yuio.parse.Path(extensions=['.bin']),
        help='input data for the model',
        flags=['-i', '--input'],
        required=True,
    )

    executor: ExecutorConfig = yuio.config.field(
        help='executor arguments',
        flags='',  # Disable prefixing executor flags with `--executor--...`
    )

    stats: set = yuio.config.field(
        default=frozenset({ModelStat.MSE, ModelStat.AUC}),
        parser=yuio.parse.FrozenSet(yuio.parse.Enum(ModelStat)),
        help='list of model statistics that needs to be exported',
    )


if __name__ == '__main__':
    config = AppConfig.load_from_args(
        '-m asd.model -i asd.bin -t 16 --stats LL ROC AUC MSE'.split()
    )
    yuio.io.info('Config = %r', config)
