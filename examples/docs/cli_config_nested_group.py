import yuio.app
import yuio.config

class GpuConfig(yuio.config.Config):
    """
    Config options for utilizing GPU resources.  [1]_

    """

    #: Enable gpu usage.
    use_gpu: bool = True

    #: Maximum amount of memory.
    max_gpu_memory: int = 1024 * 10

class ExecutorConfig(yuio.config.Config):
    """
    General executor options.

    """

    #: Number of threads to use.
    threads: int = 4

    #: Gpu config.  [2]_
    gpu_options: GpuConfig = yuio.config.inline(
        help="",  # [3]_
        # help_group=None,  [4]_
    )

@yuio.app.app
def main(
    executor_config: ExecutorConfig = yuio.app.inline(),
):
    ...

if __name__ == "__main__":
    main.run()
