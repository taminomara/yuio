import pathlib
import yuio.app
import yuio.config
import yuio.io

class ExecutorConfig(yuio.config.Config):
    #: Number of threads to use.
    threads: int = 4
    #: Enable gpu usage.
    use_gpu: bool = True

@yuio.app.app
def main(
    #: Executor options.
    executor_config: ExecutorConfig,
    #: File to process.
    input: pathlib.Path = yuio.app.positional(),
):
    yuio.io.info("executor config: `%r`", executor_config)

if __name__ == "__main__":
    main.run()
