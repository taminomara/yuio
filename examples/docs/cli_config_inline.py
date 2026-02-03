import pathlib
import yuio.app
import yuio.config

class ExecutorConfig(yuio.config.Config):
    #: Number of threads to use.
    threads: int = 4
    #: Enable gpu usage.
    use_gpu: bool = True

@yuio.app.app
def main(
    #: File to process.
    input: pathlib.Path,
    /,
    #: Executor options.
    executor_config: ExecutorConfig = yuio.app.inline(),
):
    ...

if __name__ == "__main__":
    main.run()
