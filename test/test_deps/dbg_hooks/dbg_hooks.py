# noqa: INP001
import yuio.app
import yuio.dbg


def collect_env_ok():
    return yuio.dbg.Report(
        title="Collect Env Ok",
        items=[
            "Something something",
            ("foo", "bar"),
        ],
    )


def collect_env_err():
    raise RuntimeError("something went wrong")


@yuio.app.app(version="1.0.0.1")
def main():
    pass
