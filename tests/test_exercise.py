import hashlib
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
    hash,
    InputError,
    VerificationError,
)


DI_TRAIT1 = "hot"
DI_TRAIT2 = "cold"
DI_TRAIT3 = "justright"
DI_TRAITS = [DI_TRAIT1, DI_TRAIT2, DI_TRAIT3]
DI_KEY = "test-key"
DI_DESCRIPTION = "test-description"
DI_META = {"description": DI_DESCRIPTION}

EI_VALID = json.dumps({"traits": DI_TRAITS, "key": DI_KEY, "meta": DI_META})


def test_ExerciseInput():

    input = ExerciseInput(EI_VALID)
    assert input.data == EI_VALID
    assert input.traits == DI_TRAITS
    assert input.key == DI_KEY
    assert input.description == DI_DESCRIPTION

    with pytest.raises(InputError):
        input = ExerciseInput("")

    assert input.formatted == json.dumps(json.loads(EI_VALID), indent=2)

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


def test_hash(mocker):

    mock_blake = mocker.Mock()
    mock_blake.hexdigest.return_value = "test-hash"
    mocker.patch("hashlib.blake2b", return_value=mock_blake)

    TEST_DATA = "test-data"
    TEST_KEY = "test-key"
    digest = hash(TEST_DATA, TEST_KEY)
    assert digest == "test-hash"


def test_get_hashes(mocker):
    pass
