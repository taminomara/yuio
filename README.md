# Yuio

Yuio is a lightweight python library for building simple human-friendly CLIs.

Unlike bigger tools like [`click`] or [`cleo`], Yuio is small, simple, has no dependencies, and relies
on standard python libraries such as `logging` and `argparse`. 

It is ideal for things like automation scripts, utilities for CI, or any other small tools.
Without dependencies, it is easy to use in places where you either don't or don't want to have
access to dependency management systems. Just copy-paste its source files into your project,
and be done with it.

Yuio is MyPy-friendly!

[`click`]: https://click.palletsprojects.com/
[`cleo`]: https://cleo.readthedocs.io/en/latest/

---

![A light-purple-haired catgirl smiling at you and showing heart with her hands](https://github.com/taminomara/yuio/raw/main/docs/source/_static/yuio_small.png "Picture of Yuio")

---

## Resources

- [Documentation](https://yuio.readthedocs.io/en/stable/)
- [Issues](https://github.com/taminomara/yuio/issues)
- [Source](https://github.com/taminomara/yuio/)
- [PyPi](https://pypi.org/project/yuio/)

## Requirements

The only requirement is `python >= 3.8`.

## Installation

Install `yuio` with pip:

```sh
pip3 install yuio
```

Or just copy-paste the `yuio` directory to somewhere in the `PYTHONPATH` of your project.

## Use cases

- See the [example](https://github.com/taminomara/yuio/blob/main/examples/release.py). 

## Changelog

*v1.0.0*:

- Initial release.
