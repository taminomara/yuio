import yuio.app
import yuio.config

class ExecutorConfig(yuio.config.Config):
    #: Number of threads to use.
    threads: int = 4

    #: Enable gpu usage.
    use_gpu: bool = True

@yuio.app.app
def main(
    #: Executor options.  [1]_
    #:
    #: These options control algorithm execution,
    #: resource usage, and acceleration. [2]_
    executor_config: ExecutorConfig,
):
    ...

if __name__ == "__main__":
    main.run()
