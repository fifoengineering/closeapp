# import hashlib
import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from exercise import (
    ApiRequestError,
    ApiResponseError,
    CLOSE_ENDPOINT_URL,
    CloseApi,
    ExerciseInput,
    get_hashes,
    hash,
    HashingError,
    InputError,
    main,
    VerificationError,
)


DI_TRAIT1 = "hot"
DI_TRAIT2 = "cold"
DI_TRAIT3 = "justright"
DI_TRAITS = [DI_TRAIT1, DI_TRAIT2, DI_TRAIT3]
DI_KEY = "test-key"
DI_DESCRIPTION = "test-description"
DI_META = {"description": DI_DESCRIPTION}
DI_VALID = {"traits": DI_TRAITS, "key": DI_KEY, "meta": DI_META}

EI_VALID = json.dumps(DI_VALID)

TEST_HASH = "test-hash"


def test_ExerciseInput():

    input = ExerciseInput(EI_VALID)
    assert input.data_str == EI_VALID
    assert input.traits == DI_TRAITS
    assert input.key == DI_KEY
    assert input.description == DI_DESCRIPTION

    with pytest.raises(InputError):
        input = ExerciseInput("")

    assert input.formatted == json.dumps(DI_VALID, indent=2)

    EI_INVALID1 = json.dumps({"key": DI_KEY, "meta": DI_META})

    with pytest.raises(InputError) as e:
        input = ExerciseInput(EI_INVALID1)
    assert e.type is InputError
    assert e.value.args[0] == "Missing key 'traits' in decoded input data"


def test_CloseApi():
    api = CloseApi()
    assert api.url == CLOSE_ENDPOINT_URL
    api = CloseApi(url="test")
    assert api.url == "test"


def test_CloseApi_get_exercise_input(httpx_mock: HTTPXMock):

    api = CloseApi()

    httpx_mock.add_response(text=EI_VALID)
    input = api.get_exercise_input()
    assert input.traits == DI_TRAITS

    httpx_mock.add_exception(httpx.RequestError("testing request errors"))
    with pytest.raises(ApiRequestError) as e:
        api.get_exercise_input()

    httpx_mock.add_exception(
        httpx.HTTPStatusError(
            "test status error",
            request=httpx.Request("GET", api.url),
            response=httpx.Response(400),
        )
    )
    with pytest.raises(ApiResponseError) as e:
        api.get_exercise_input()
    assert e.value.status_code == 400


def test_CloseApi_get_verification_id(httpx_mock: HTTPXMock):

    api = CloseApi()

    hashes = ["a", "b", "c"]
    TEST_VID = "Verification ID: test-id"
    httpx_mock.add_response(method="POST", text=TEST_VID)
    vid = api.get_verification_id(hashes)
    assert vid == TEST_VID

    httpx_mock.add_exception(httpx.RequestError("testing request errors"))
    with pytest.raises(ApiRequestError) as e:
        api.get_verification_id(hashes)

    httpx_mock.add_exception(
        httpx.HTTPStatusError(
            "test status error",
            request=httpx.Request("GET", api.url),
            response=httpx.Response(503),
        )
    )
    with pytest.raises(ApiResponseError) as e:
        api.get_verification_id(hashes)
    assert e.value.status_code == 503

    httpx_mock.add_exception(
        httpx.HTTPStatusError(
            "test status error",
            request=httpx.Request("GET", api.url),
            response=httpx.Response(400),
        )
    )
    with pytest.raises(VerificationError) as e:
        api.get_verification_id(hashes)


def test_hash_success(mocker):
    mock_cls = mocker.patch("hashlib.blake2b")
    mock_cls.return_value.hexdigest.return_value = TEST_HASH
    assert hash("val", "key") == TEST_HASH
    mock_cls.assert_called_once_with(
        "val".encode(),
        key="key".encode(),
    )


def test_hash_HashingError(mocker):
    mock_cls = mocker.patch("hashlib.blake2b")
    mock_cls.return_value.hexdigest.side_effect = Exception("some exception")
    with pytest.raises(HashingError) as e:
        hash("val", "key")
    assert e.type is HashingError


def test_get_hashes(mocker):
    mock_func = mocker.patch("exercise.hash")
    mock_func.return_value = TEST_HASH
    hashes = get_hashes(["a", "b"], "key")
    assert hashes == [TEST_HASH, TEST_HASH]
    mock_func.assert_has_calls(
        [
            mocker.call("a", "key"),
            mocker.call("b", "key"),
        ]
    )


def test_main_success(mocker, capsys):

    # mock ExerciseInput-like object
    mock_input = mocker.Mock()
    mock_input.formatted = "formatted json"
    mock_input.traits = ["hot", "cold"]
    mock_input.key = "abc123"

    # mock CloseApi instance
    mock_api = mocker.Mock()
    mock_api.get_exercise_input.return_value = mock_input
    mock_api.get_verification_id.return_value = "Verification ID: test-id"

    # patch CloseApi constructor
    mocker.patch("exercise.CloseApi", return_value=mock_api)

    # patch hashing function
    mocker.patch("exercise.get_hashes", return_value=["hash1", "hash2"])

    # run main
    main()

    # capture stdout
    captured = capsys.readouterr()

    # assertions
    assert "Exercise input data" in captured.out
    assert "hash1" in captured.out
    assert "Verification ID: test-id" in captured.out
    assert "Exercise complete" in captured.out

    # verify calls
    mock_api.get_exercise_input.assert_called_once()

    mock_api.get_verification_id.assert_called_once_with(["hash1", "hash2"])
