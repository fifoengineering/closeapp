"""close.com backend engineering application exercise

A script to generate a verification id to submit with a close.com job
application.  The close.com job application URL:

    https://close.com/careers?ashby_jid=01fc4ad7-4d33-4f64-919f-502bb2c20efc

Application directions:

    Send a GET request to https://api.close.com/buildwithus/
    Follow the instructions provided in the response. Enter your
    Verification ID in the space provided here.

Endpoint response directions:

    Enclosed are some traits that [Joe](https://www.linkedin.com/in/jkemp101/)
    believes great engineers exhibit. Using the included UTF-8 `key`, construct
    a JSON array using the lowercase hex digest of the blake2b hash for each
    trait (digest size=64). POST this bare array back to this endpoint. Example
    array: [\"1f9ec19c7...57fd27e5\", \"79c72b47088...bf13026c\", ...] If the
    hashes are correct you will get a Verification ID you should include in
    your application. 400 responses indicate a problem with the hashes in your
    array. Note, the key rotates each day around midnight EST.
"""

import argparse
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_ENDPOINT_URL = "https://api.close.com/buildwithus/"


log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
  """Detect debug flag passed in from command line"""

  parser = argparse.ArgumentParser()
  parser.add_argument("--debug", action="store_true")
  return parser.parse_args()


def configure_logging(debug: bool) -> None:
  """Set log formatting, supports debug mode"""

  level = logging.DEBUG if debug else logging.ERROR
  logging.basicConfig(
    level=level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
  )


class ExerciseError(Exception):
  """Base exception for exercise providing user friendly display message"""

  default_user_msg = "Exercise error"

  def __init__(self, message: str, user_msg: str | None = None):
    super().__init__(message)
    self.user_msg = user_msg or self.default_user_msg


class InputError(ExerciseError):
  """Error processing input data"""

  default_user_msg = "Unable to process exercise input data"


class ApiRequestError(ExerciseError):
  """Failed to send request to API"""

  default_user_msg = "Unable to send request message to api endpoint"


class ApiResponseError(ExerciseError):
  """Error response received from API indicated with a status code"""

  default_user_msg = "Received error status code response from api endpoint"

  def __init__(
    self, message: str, *, status_code: int, user_msg: str | None = None
  ):
    super().__init__(message, user_msg=user_msg)
    self.status_code = status_code


class HashingError(ExerciseError):
  """Error related to generating hashed data for verification"""

  default_user_msg = "Failed to generate exercise hash values"


class VerificationError(ExerciseError):
  """Error related to verification of hashvalues"""

  default_user_msg = "Hash values sent for verification were incorrect"


@dataclass(frozen=True)
class ExerciseInput:
  """Input data for a coding exercise, obtained from close.com endpoint"""

  traits: list[str]
  key: str
  description: str

  @classmethod
  def from_json(cls, data_str: str) -> "ExerciseInput":
    """Create an instance from a JSON formatted input string.

    Expected JSON:

    {
        "traits": ["t1", "t2", "t3"],
        "key": "value",
        "meta": {
            "description": "str"
        }
    }
    """

    try:
      data = json.loads(data_str)
      if not isinstance(data, dict):
        raise InputError("JSON root must be an object structure.")

      traits = data["traits"]
      if not isinstance(traits, list) or not all(
        isinstance(v, str) for v in traits
      ):
        raise InputError(
          f"Input value for key 'traits' must be list[str] (received {traits})"
        )

      key = data["key"]
      if not isinstance(key, str):
        raise InputError(
          f"Input value for key 'key' must be str (received {key})"
        )

      meta = data["meta"]
      if not isinstance(meta, dict):
        raise InputError(
          f"Input value for key 'meta' must be dict (received {meta})"
        )

      description = meta["description"]
      if not isinstance(description, str):
        raise InputError(
          "Input value for meta.description must "
          f"be str (received {description})"
        )

      return cls(traits, key, description)

    except (ValueError, TypeError) as err:
      raise InputError("JSON decoding error on input") from err

    except KeyError as err:
      raise InputError(f"Missing key {err}") from err


@dataclass(frozen=True)
class VerificationResponse:
  verification_id: str


class CloseApi:
  """A class managing requests to Close.com api"""

  def __init__(
    self,
    client: httpx.Client,
    url: str = DEFAULT_ENDPOINT_URL,
  ) -> None:
    self.client = client
    self.url = url

  def _request(self, method: str, **kwargs: Any) -> httpx.Response:
    """Sends requests with the specified method (GET, POST, etc.)"""

    try:
      log.debug("Sending %s request to URL: %s", method, self.url)
      response = self.client.request(method, self.url, **kwargs)
      log.debug(
        "Response received from %s (%s)", self.url, response.status_code
      )
      response.raise_for_status()
      return response

    except httpx.RequestError as err:
      raise ApiRequestError(
        f"Failed to send request to url '{self.url}'"
      ) from err

    except httpx.HTTPStatusError as err:
      sc = err.response.status_code
      raise ApiResponseError(
        f"Invalid response status code {sc}", status_code=sc
      ) from err

  def get_input(self) -> ExerciseInput:
    """Fetches exercise input from close.com, returns data as
    ExerciseInput."""

    response = self._request("GET")
    return ExerciseInput.from_json(response.text)

  def verify_hashes(self, hashes: list[str]) -> VerificationResponse:
    """Requests verification of hashed input data from close.com,
    returns VerificationResponse if successful.
    """

    try:
      response = self._request("POST", json=hashes)

      response_text = response.text.strip()

      prefix = "Verification ID:"
      if not response_text.startswith(prefix):
        raise VerificationError(
          f"Unexpected verification response: '{response_text}'"
        )

      verification_id = response_text.removeprefix(prefix).strip()
      if not verification_id:
        raise VerificationError(
          f"Blank verification ID in response: '{response_text}'"
        )

      return VerificationResponse(verification_id)

    except ApiResponseError as err:
      # intercept 400 status code errors and convert to
      # a verification error as indicated by directions
      if err.status_code == 400:
        raise VerificationError("Invalid hash data") from err
      raise


def generate_hash(data: str, key: str) -> str:
  """Generates str hash value as blake2 hash digest using provided
  data and key"""

  try:
    # defaults of "utf-8" and digest size of 64 assumed...
    bkey, bdata = key.encode(), data.encode()
    hasher = hashlib.blake2b(bdata, key=bkey)
    return hasher.hexdigest()

  except (ValueError, TypeError) as exc:
    raise HashingError("Unable to generate hash value") from exc


def generate_hash_list(values: list[str], key: str) -> list[str]:
  """Hashes a list of strs with the provided key"""

  hashes = [generate_hash(v, key) for v in values]
  return hashes


@dataclass(frozen=True)
class ExerciseResult:
  """Encapsulates exercise input and output"""

  input_data: ExerciseInput
  hashes: list[str]
  verification: VerificationResponse


def run_exercise() -> ExerciseResult:
  """Runs the close.com code exercise

  Fetches input data (including trait list and daily rotating hashing key)
  from a close.com endpoint, hashes the list values and submits the resulting
  hashes to close.com to obtain a verification id.
  """

  with httpx.Client(timeout=10.0) as client:
    api = CloseApi(client)
    exercise_input = api.get_input()
    hashes = generate_hash_list(exercise_input.traits, exercise_input.key)
    verification = api.verify_hashes(hashes)
    return ExerciseResult(exercise_input, hashes, verification)


def display_result(result: ExerciseResult) -> None:
  """Displays exercise results"""

  def labeled_data(label, data) -> str:
    return f"{label}\n{'-' * len(label)}\n{data}"

  hash_str = ", ".join([f'"{h}"' for h in result.hashes])
  output = [
    "Close.com application code exercise",
    "INPUT",
    labeled_data("Description", result.input_data.description),
    labeled_data("Traits", ", ".join(result.input_data.traits)),
    labeled_data("Key", result.input_data.key),
    "OUTPUT",
    labeled_data("Hashed Traits", hash_str),
    labeled_data("Verification ID", result.verification.verification_id),
  ]

  display_str = "\n\n".join(output)
  print(f"\n{display_str}\n")


def main() -> None:

  args = parse_args()
  configure_logging(args.debug)

  try:
    result = run_exercise()
    display_result(result)

  except ExerciseError as err:
    log.exception("Exercise failure")
    print(err.user_msg)

  except Exception:
    log.exception("Unexpected error")
    print("Unexpected error encountered")


if __name__ == "__main__":  # pragma: no cover
  main()
