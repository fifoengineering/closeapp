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


@pytest.fixture
def blake_instance(mocker):
    blake_inst = mocker.Mock()
    blake_inst.hexdigest.return_value = TEST_HASH
    return blake_inst


@pytest.fixture
def blake_class(mocker, blake_instance):
    blake_cls = mocker.patch("hashlib.blake2b", return_value=blake_instance)
    return blake_cls


def test_hash(blake_class, blake_instance):
    val = "test-val"
    key = "test-key"
    digest = hash(val, key)
    assert digest == TEST_HASH
    blake_class.assert_called_once_with(val.encode(), key=key.encode())
    blake_instance.hexdigest.assert_called_once()

    blake_class.side_effect = Exception("test error handling")
    with pytest.raises(HashingError) as e:
        digest = hash(val, key)
    assert e.type is HashingError


def test_get_hashes(mocker, blake_class, blake_instance):
    vals = ["a", "b"]
    key = "test-key"
    hashes = get_hashes(vals, key)
    blake_class.assert_has_calls(
        [
            mocker.call("a".encode(), key=key.encode()),
            mocker.call("b".encode(), key=key.encode()),
        ]
    )
    blake_instance.hexdigest.assert_has_calls(
        [
            mocker.call(),
            mocker.call(),
        ]
    )
    assert hashes == [TEST_HASH, TEST_HASH]


@pytest.fixture
def input(mocker):
    input_inst = mocker.Mock()
    input_inst.formatted.return_value = "test-formatted"
    input_cls = mocker.patch("exercise.ExerciseInput", return_value=input_inst)
    return input_cls


@pytest.fixture
def api(mocker, input):
    api_cls = mocker.patch("exercise.CloseApi", return_value=input)
    return api_cls


from unittest.mock import patch
from exercise import ExerciseInput
import exercise


def test_main_InputError(mocker, capsys, api, input):

    print(f"input={input}")

    with patch("exercise.ExerciseInput") as MockExerciseInput:
        mock_inst = MockExerciseInput.return_value
        mock_inst.npformatted.return_value = "test-formatted-2"

        print(exercise.getFormatted())

        test_inp = exercise.ExerciseInput()

        print(f"test_inp={test_inp}")
        print(f"test_inpt.npformatted={test_inp.npformatted()}")

    # test_inp = input(123)
    # print(f"test_inp={test_inp}")

    # test_inp2 = ExerciseInput("asdf")
    # print(f"test_inp2={test_inp2}")

    # api = mocker.patch("exercise.CloseApi")
    # api.get_exercise_input.return_value = "test-input"
    # api.get_verification_id.return_value = "test-vid"
    # print(api.get_exercise_input())
    # print(api.get_verification_id())
    # cap = capsys.readouterr()
    # print(cap.out)


def test_monkey_patching(monkeypatch):
    # monkeypatch(
    #    exercise,
    #    "ExerciseInput",
    # )
    pass
