import pathlib

import yuio.app
import yuio.config
import yuio.io
import yuio.parse


class Config(yuio.config.Config):
    """global configuration

    global options are loaded from `./app_config.json`,
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

    yuio.io.info('global config is loaded: `%r`', CONFIG)


main.usage = """
%(prog)s [-q] [-f] [-m] [<branch>]
%(prog)s [-q] [-f] [-m] --detach [<branch>]
%(prog)s [-q] [-f] [-m] [--detach] <commit>
...
"""

main.epilog = """
formatting:
    prolog is parsed and colorized according to the general format
    of help messages:

    - lines without indent that end with semicolon are considered headings;
    - the rest of the lines are considered heading sections --
      they are indented accordingly;
    - some markdown-like block markup is supported: code snippets, bullet
      and numbered lists, quotes. For example, here's a code block:

      ```
      Beautiful python
      Explicit and simple form
      Winding through clouds

          -- from heroku art
      ```

      ```sh
      cat foo.txt | grep -e "ERROR" | less && echo "1" || true && git add 1;
      ```

      And here's another one, with syntax highlighting:

      ```py
      for i in range(10):
          print(f"Hello, {i}!")
      ```

    - Color tags are supported, as well as `backticks`! Btw, backticks highlight
      `--flags` with appropriate color too!

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

    yuio.io.info('applying model `%s` to data `%s`', model, data)


@main.subcommand(aliases=['t'])
def train(
    #: input data for the model
    data: pathlib.Path = yuio.config.positional(),

    #: output data for the model
    output: pathlib.Path = yuio.config.field(
        default=pathlib.Path('trained.model'),
        flags=['-o', '--out', '--output'],
    ),
):
    """train model on a dataset.

    """

    yuio.io.info('training model `%s` on data `%s`', output, data)


if __name__ == '__main__':
    main.run()
