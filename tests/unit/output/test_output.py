import logging

import pytest
from funcy import first
from voluptuous import MultipleInvalid, Schema

from dvc.cache import NamedCache
from dvc.ignore import _no_match
from dvc.output import CHECKSUM_SCHEMA, BaseOutput


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", None),
        (None, None),
        (11111, "11111"),
        ("11111", "11111"),
        ("aAaBa", "aaaba"),
        (
            "3cc286c534a71504476da009ed174423",
            "3cc286c534a71504476da009ed174423",
        ),  # md5
        (
            "d41d8cd98f00b204e9800998ecf8427e-38",
            "d41d8cd98f00b204e9800998ecf8427e-38",
        ),  # etag
        (
            "000002000000000000000000c16859d1d071c6b1ffc9c8557d4909f1",
            "000002000000000000000000c16859d1d071c6b1ffc9c8557d4909f1",
        ),  # hdfs checksum
        # Not much we can do about hex and oct values without writing our own
        # parser. So listing these test cases just to acknowledge this.
        # See https://github.com/iterative/dvc/issues/3331.
        (0x3451, "13393"),
        (0o1244, "676"),
    ],
)
def test_checksum_schema(value, expected):
    assert Schema(CHECKSUM_SCHEMA)(value) == expected


@pytest.mark.parametrize("value", ["1", "11", {}, {"a": "b"}, [], [1, 2]])
def test_checksum_schema_fail(value):
    with pytest.raises(MultipleInvalid):
        assert Schema(CHECKSUM_SCHEMA)(value)


@pytest.mark.parametrize(
    "exists, expected_message",
    [
        (
            False,
            (
                "Output 'path'(stage: 'stage.dvc') is missing version info. "
                "Cache for it will not be collected. "
                "Use `dvc repro` to get your pipeline up to date."
            ),
        ),
        (
            True,
            (
                "Output 'path'(stage: 'stage.dvc') is missing version info. "
                "Cache for it will not be collected. "
                "Use `dvc repro` to get your pipeline up to date.\n"
                "You can also use `dvc commit stage.dvc` to associate "
                "existing 'path' with stage: 'stage.dvc'."
            ),
        ),
    ],
)
def test_get_used_cache(exists, expected_message, mocker, caplog):
    stage = mocker.MagicMock()
    mocker.patch.object(stage, "__str__", return_value="stage: 'stage.dvc'")
    mocker.patch.object(stage, "addressing", "stage.dvc")
    mocker.patch.object(
        stage.repo.tree.dvcignore,
        "check_ignore",
        return_value=_no_match("path"),
    )

    output = BaseOutput(stage, "path")

    mocker.patch.object(output, "use_cache", True)
    mocker.patch.object(stage, "is_repo_import", False)
    mocker.patch.object(
        BaseOutput, "checksum", new_callable=mocker.PropertyMock
    ).return_value = None
    mocker.patch.object(
        BaseOutput, "exists", new_callable=mocker.PropertyMock
    ).return_value = exists

    with caplog.at_level(logging.WARNING, logger="dvc"):
        assert isinstance(output.get_used_cache(), NamedCache)
    assert first(caplog.messages) == expected_message
