import json

import httpx
import pytest

from exercise import (
  DEFAULT_ENDPOINT_URL,
  ApiRequestError,
  ApiResponseError,
  CloseApi,
  ExerciseInput,
  ExerciseResult,
  HashingError,
  InputError,
  VerificationError,
  VerificationResponse,
  display_result,
  generate_hash,
  generate_hash_list,
  main,
  run_exercise,
)

INP_TRAIT1 = "hot"
INP_TRAIT2 = "cold"
INP_TRAITS = [INP_TRAIT1, INP_TRAIT2, "just right"]
INP_KEY = "test-key"
INP_DESC = "test-description"
INP_META = {"description": INP_DESC}
INP_OBJ = {"traits": INP_TRAITS, "key": INP_KEY, "meta": INP_META}

# generated from INP_TRAIT1/INP_TRAIT2 & INP_KEY ("hot"/"cold" & "test-key")
TRAIT1_KEY_DIGEST = (
  "dce23ca22894404d37feb6d0c40dbd2a08f46798ce737597168677a84ee99eab"
  "118f92b2b9094c46c0be2ab24e0cece16ad9039704bb2a1ffa0d8fe05a7d0d18"
)
TRAIT2_KEY_DIGEST = (
  "0a70b5e757c59dfd77df4e70e739420b9c6500e6350356f159ee8b75820f6c2e"
  "a18be11c3095b3d0e3eceb74af770a3a80de4f7033a08246d5f8540c1beb22e8"
)


@pytest.fixture
def json_input():
  return json.dumps(INP_OBJ)


def test_ExerciseInput_from_json_success(json_input):
  exercise_input = ExerciseInput.from_json(json_input)
  assert exercise_input.traits == INP_TRAITS
  assert exercise_input.key == INP_KEY
  assert exercise_input.description == INP_DESC


@pytest.mark.parametrize(
  "json_data, error_text",
  [
    (
      '{"key": "asdf"',
      "JSON decoding error on input",
    ),
    (
      '"plain-str"',
      "JSON root must be an object",
    ),
    (
      {"key": INP_KEY, "meta": INP_META},
      "Missing key 'traits'",
    ),
    (
      {"key": INP_KEY, "meta": INP_META, "traits": 123},
      "'traits' must be list[str]",
    ),
    (
      {"key": INP_KEY, "meta": INP_META, "traits": [1, 2]},
      "'traits' must be list[str]",
    ),
    (
      {"key": 321, "meta": INP_META, "traits": ["a", "b"]},
      "'key' must be str",
    ),
    (
      {"key": INP_KEY, "meta": 123, "traits": ["a", "b"]},
      "'meta' must be dict",
    ),
    (
      {"key": INP_KEY, "meta": {}, "traits": ["a", "b"]},
      "Missing key 'description'",
    ),
    (
      {
        "key": INP_KEY,
        "meta": {"description": 123},
        "traits": ["a", "b"],
      },
      "meta.description must be str",
    ),
  ],
)
def test_ExerciseInput_from_json_input_errors(json_data, error_text):
  json_str = json_data if isinstance(json_data, str) else json.dumps(json_data)
  with pytest.raises(InputError) as e:
    ExerciseInput.from_json(json_str)
  assert error_text in str(e.value)


def test_VerificationResponse():
  ver_id = "test-123"
  ver_resp = VerificationResponse(ver_id)
  assert ver_resp.verification_id == ver_id


def test_CloseApi_instantiation():
  with httpx.Client() as client:
    api = CloseApi(client)
    assert api.url == DEFAULT_ENDPOINT_URL
    assert api.client == client
    api = CloseApi(client, url="test")
    assert api.url == "test"


@pytest.fixture
def api():
  with httpx.Client() as client:
    yield CloseApi(client)


def test_CloseApi_get_input_success(httpx_mock, api, json_input):
  httpx_mock.add_response(text=json_input)
  exercise_input = api.get_input()
  assert exercise_input.traits == INP_TRAITS
  assert exercise_input.key == INP_KEY
  assert exercise_input.description == INP_DESC


def test_CloseApi_get_input_request_error(httpx_mock, api):
  httpx_mock.add_exception(httpx.RequestError("testing request errors"))
  with pytest.raises(ApiRequestError):
    api.get_input()


def test_CloseApi_get_input_response_error(httpx_mock, api):
  httpx_mock.add_exception(
    httpx.HTTPStatusError(
      "test status error",
      request=httpx.Request("GET", api.url),
      response=httpx.Response(400),
    )
  )
  with pytest.raises(ApiResponseError) as e:
    api.get_input()
  assert e.value.status_code == 400


def test_CloseApi_verify_hashes_success(httpx_mock, api):
  ver_id = "test-id"
  httpx_mock.add_response(method="POST", text=f"Verification ID: {ver_id}")
  assert api.verify_hashes(["a", "b", "c"]).verification_id == ver_id


def test_CloseApi_verify_hashes_request_error(httpx_mock, api):
  httpx_mock.add_exception(httpx.RequestError("testing request errors"))
  with pytest.raises(ApiRequestError):
    api.verify_hashes(["a", "b", "c"])


def test_CloseApi_verify_hashes_response_error(httpx_mock, api):
  httpx_mock.add_response(
    method="POST", status_code=503, text="service unavailable"
  )
  with pytest.raises(ApiResponseError) as e:
    api.verify_hashes(["a", "b"])
  assert "Invalid response status code" in str(e.value)


@pytest.mark.parametrize(
  "status_code, resp_text, error_msg",
  [
    (200, "(invalid): test-id", "Unexpected verification response"),
    (200, "Verification ID: ", "Blank verification ID"),
    (400, "server error", "Invalid hash data"),
  ],
)
def test_CloseApi_verify_hashes_verification_errors(
  httpx_mock, api, status_code, resp_text, error_msg
):
  httpx_mock.add_response(
    method="POST", status_code=status_code, text=resp_text
  )
  with pytest.raises(VerificationError) as e:
    api.verify_hashes(["a", "b"])
  assert error_msg in str(e.value)


def test_generate_hash_success():
  assert generate_hash(INP_TRAIT1, INP_KEY) == TRAIT1_KEY_DIGEST
  assert generate_hash(INP_TRAIT2, INP_KEY) == TRAIT2_KEY_DIGEST


def test_generate_hash_hashing_error(mocker):
  mocker.patch("hashlib.blake2b", side_effect=ValueError("hashing exception"))
  with pytest.raises(HashingError):
    generate_hash("val", "key")


def test_generate_hash_list():
  hashes = generate_hash_list([INP_TRAIT1, INP_TRAIT2], INP_KEY)
  assert hashes == [TRAIT1_KEY_DIGEST, TRAIT2_KEY_DIGEST]


@pytest.fixture
def exercise_input():
  return ExerciseInput(traits=INP_TRAITS, key=INP_KEY, description=INP_DESC)


def test_ExerciseResult(exercise_input):
  hashes = ["a", "b"]
  ver_id = "test-ver-id"
  ver_resp = VerificationResponse(ver_id)
  result = ExerciseResult(exercise_input, hashes, ver_resp)
  assert result.input_data.key == INP_KEY
  assert result.hashes == hashes
  assert result.verification.verification_id == ver_id


def test_run_exercise(mocker, exercise_input):
  mock_api = mocker.Mock()
  mock_api.get_input.return_value = exercise_input
  ver_id = "test-ver-id"
  mock_api.verify_hashes.return_value = VerificationResponse(ver_id)
  mocker.patch("exercise.CloseApi", return_value=mock_api)

  hashes = ["a", "b"]
  mock_hasher = mocker.patch("exercise.generate_hash_list", return_value=hashes)

  result = run_exercise()

  mock_api.get_input.assert_called_once()
  mock_hasher.assert_called_once_with(exercise_input.traits, exercise_input.key)
  mock_api.verify_hashes.assert_called_once_with(hashes)
  assert isinstance(result, ExerciseResult)
  assert result.input_data.key == INP_KEY
  assert result.verification.verification_id == ver_id


def test_display_result(capsys, exercise_input):
  hash1 = "hash1"
  hash2 = "hash2"
  ver_id = "test-ver-id"
  display_result(
    ExerciseResult(exercise_input, [hash1, hash2], VerificationResponse(ver_id))
  )
  captured = capsys.readouterr()
  assert INP_TRAIT1 in captured.out
  assert INP_KEY in captured.out
  assert hash1 in captured.out
  assert hash2 in captured.out
  assert ver_id in captured.out


def test_main_success(mocker):
  mock_parse = mocker.patch(
    "exercise.parse_args", return_value=mocker.Mock(debug=False)
  )
  mock_config = mocker.patch("exercise.configure_logging")
  mock_result = mocker.Mock()
  mock_run = mocker.patch("exercise.run_exercise", return_value=mock_result)
  mock_display = mocker.patch("exercise.display_result")

  main()

  mock_parse.assert_called_once()
  mock_config.assert_called_once_with(False)
  mock_run.assert_called_once()
  mock_display.assert_called_once_with(mock_result)


def test_main_exercise_error(mocker, capsys):
  underlying_msg = "underlying error message"
  mocker.patch(
    "exercise.run_exercise",
    side_effect=InputError(underlying_msg),
  )
  mock_log = mocker.patch("exercise.log.exception")

  main()

  captured = capsys.readouterr()
  assert "Unable to process exercise input data" in captured.out
  assert underlying_msg not in captured.out
  mock_log.assert_called_once_with("Exercise failure")


def test_main_fallback_error_handling(mocker, capsys):
  underlying_msg = "underlying error message"
  mocker.patch(
    "exercise.run_exercise", side_effect=RuntimeError(underlying_msg)
  )
  mock_log = mocker.patch("exercise.log.exception")

  main()

  captured = capsys.readouterr()
  assert "Unexpected error encountered" in captured.out
  assert underlying_msg not in captured.out
  mock_log.assert_called_once_with("Unexpected error")
