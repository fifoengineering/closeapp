"""close.com backend engineering application exercise

A script to generate a verification id to submit with a close.com job
application.  Job application form on close.com:

    https://close.com/careers?ashby_jid=01fc4ad7-4d33-4f64-919f-502bb2c20efc

Application directions:

    Send a GET request to https://api.close.com/buildwithus/
    Follow the instructions provided in the response. Enter your
    Verification ID in the space provided here.

Instructions obtained from endpoint response:

    Enclosed are some traits that [Joe](https://www.linkedin.com/in/jkemp101/)
    believes great engineers exhibit. Using the included UTF-8 `key`, construct
    a JSON array using the lowercase hex digest of the blake2b hash for each
    trait (digest size=64). POST this bare array back to this endpoint. Example
    array: [\"1f9ec19c7...57fd27e5\", \"79c72b47088...bf13026c\", ...] If the
    hashes are correct you will get a Verification ID you should include in
    your application. 400 responses indicate a problem with the hashes in your
    array. Note, the key rotates each day around midnight EST.
"""

import hashlib
import json
import logging
import sys

import httpx

if "debug" in sys.argv:
    level = logging.DEBUG
elif "info" in sys.argv:
    level = logging.INFO
else:
    level = logging.ERROR

logging.basicConfig(
    level=level, format="%(asctime)s %(levelname)-6s %(message)s"
)
log = logging.getLogger()


CLOSE_ENDPOINT_URL = "https://api.close.com/buildwithus/"


class InputError(Exception):
    """Error processing input data"""


class ApiRequestError(Exception):
    """Failed to send request to API"""


class ApiResponseError(Exception):
    """Error response received from API indicated with a status code"""

    def __init__(self, message: str, *, status_code: int):
        Exception.__init__(self, message)
        self.status_code = status_code


class VerificationError(Exception):
    """Error related to verification of hash values"""


class ExerciseInput:
    """Input data for a coding exercise

    Parses a JSON encoded input string into fields for use as input
    in a coding exercise.
    """

    def __init__(self, data: str):
        """Initialize instance of exercise input

        Expected format of JSON input:
        {
            "traits": ["t1", "t2", "t3],
            "key": "value",
            "meta": {
                "description": "str"
            }
        }

        Args:
            data: string containing JSON data to decode

        Raises:
            InputError if an error occurs during JSON decoding or expected
            field is missing
        """
        try:
            log.debug("Processing encoded input data: %s", data)
            self.data = data
            decoded = json.loads(data)
            self.traits = decoded["traits"]
            self.key = decoded["key"]
            self.description = decoded["meta"]["description"]

        except ValueError as err:
            raise InputError("JSON decoding error on input") from err
        except KeyError as err:
            raise InputError(
                f"Missing key {err} in decoded input data"
            ) from err

    @property
    def formatted(self):
        """Displays the JSON encoded input data with indentation"""
        return json.dumps(json.loads(self.data), indent=2)


class CloseApi:
    """A class managing requests to Close.com api

    Sends requests to an API provided by Close.com
    """

    def __init__(self, url: str = CLOSE_ENDPOINT_URL) -> None:
        """Initialize an instance of an API request manager.

        Args:
            url: a string endpoint URL to send requests to
        """
        self.url = url
        log.debug(f"CloseApi initialized with endpoint URL: '{self.url}'.")

    def get_exercise_input(self) -> ExerciseInput:
        """Fetch exercise input data

        Sends GET request to Close.com endpoint, loads response text into
        ExerciseInput object.

        Returns:
            Response data as an ExerciseInput object

        Raises:
            ApiRequestError if request failed to send
            ApiResponseError if bad status code received in response
            InputError if unable to process response text into ExerciseInput
        """

        try:
            log.info("Requesting exercise input data from Close.com...")

            with httpx.Client() as client:
                rsp = client.get(self.url)
            input = ExerciseInput(rsp.text)

            log.info("Exercise input received.")

            return input

        except httpx.HTTPStatusError as err:
            sc = err.response.status_code
            raise ApiResponseError(
                f"Invalid response status code {sc}", status_code=sc
            ) from err

        except httpx.RequestError as err:
            raise ApiRequestError(
                f"Failed to send request to url '{self.url}'"
            ) from err

    def get_verification_id(self, hashes: list[str]) -> str:
        """Requests verification ID

        Sends POST request with JSON encoded list of hashed traits.

        Args:
            hashes: list of strings containing the hashed trait values
                obtained from the exercise input
        Returns:
            response text as string from Close.com api

        Raises:
            ApiRequestError if request send failed
            VerificationError if 400 status code received
            ApiResponseError if invalid non-400 status code received
        """
        try:
            log.info("Requesting verification ID from Close.com...")

            with httpx.Client() as client:
                rsp = client.post(self.url, json=hashes)

            log.info("Verification ID received.")

            return rsp.text

        except httpx.HTTPStatusError as err:
            # 400 from API indicates incorrect hash values
            sc = err.response.status_code
            if sc == 400:
                raise VerificationError("Invalid hash data in request")

            raise ApiResponseError(
                f"Invalid response status code {sc}", status_code=sc
            ) from err

        except httpx.RequestError as err:
            raise ApiRequestError(
                f"Failed to send request to url '{self.url}'"
            ) from err


class HashingError(Exception):
    """Error related to generating hashed data for verification"""


def hash(data: str, key: str) -> str:
    """Generate a hash value from data and key using blake2 hash function

    Uses standard library hashlib.blake2b hasher to hash the data with
    the provided key.

    Returns:
        Hashed data in a string

    Raises:
        HashingError if invalid encoding given or other error encounterd
    """
    try:
        # defaults of "utf-8" and digest size of 64 assumed...
        bkey = key.encode()
        bdata = data.encode()
        hasher = hashlib.blake2b(bdata, key=bkey)
        return hasher.hexdigest()

    except Exception as exc:
        raise HashingError("Unable to generate hash value") from exc


def get_hashes(values: list[str], key: str) -> list[str]:
    """Hash a list of strings

    Args:
        values: list of strings to generate hash digests of
        key: string to use as hashing key

    Returns:
        list of string hash digests of the original items

    Raises:
        HashingError if hash call
    """
    hashes = [hash(v, key) for v in values]
    return hashes


def main():
    try:
        log.info("Close.com application exercise started.")

        # fetch input
        api = CloseApi()
        input = api.get_exercise_input()

        print(f"Exercise input data:\n\n{input.formatted}\n")

        # generate hash digests from trait data
        hashes = get_hashes(input.traits, input.key)

        print(f"Hashed traits:\n\n{'\n'.join(hashes)}\n")

        # verify hashes
        verificationId = api.get_verification_id(hashes).strip()
        if not verificationId.startswith("Verification ID"):
            raise VerificationError(
                "Unexpected verification response"
                f" from endpoint: '{verificationId}'"
            )

        print(f"{verificationId}\n")

        print("Exercise complete.\n")

    except InputError as err:
        log.exception(err)
        print("Unable to process exercise input data")

    except ApiRequestError as err:
        log.exception(err)
        print("Unable to send API request")

    except ApiResponseError as err:
        log.exception(err)
        print("Received an error response from API endpoint")

    except HashingError as err:
        log.exception(err)
        print("Error during hashing of input data")

    except VerificationError as err:
        log.exception(err)
        print("Hash value verification failed")

    except Exception as exc:
        log.exception(exc)
        print("Unexpected error encountered, exercise failed")


if __name__ == "__main__":
    # main()
    main()
