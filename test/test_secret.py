import yuio.secret


def test_basics():
    s = yuio.secret.SecretValue("asd")
    assert str(s) == "***"
    assert repr(s) == "SecretValue(***)"

    s = yuio.secret.SecretValue("")
    assert str(s) == "***"
    assert repr(s) == "SecretValue(***)"
