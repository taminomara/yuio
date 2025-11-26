import yuio.dbg  # noqa: INP001


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
