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

from hashlib import blake2b
import json
import logging
import sys

import httpx

level = logging.DEBUG if "debug" in sys.argv else logging.INFO
test_ind = "(TEST) " if "test" in sys.argv else ""
logging.basicConfig(
    level=level, format=f"%(asctime)s %(levelname)-6s {test_ind}%(message)s"
)
log = logging.getLogger()


CLOSE_ENDPOINT_URL = "https://api.close.com/buildwithus/"
INPUT_FILENAME = "input.json"


def show_usage_and_exit(msg: str, exit_code=-1):
    """Displays script usage help message, exits"""
    print(f"""
{msg}

Run this script to generate a Validation ID for a close.com job application.
                    
Valid command line arguments:

    test  execute exercise steps from locally loaded data
    debug set log level to DEBUG
""")
    exit(exit_code)


def get_options():
    """Validate and process command line args to get options

    Current options allow debug level logging to be set and running
    exercise in test mode.
    """

    args = sys.argv[1:]

    allowed = ["test", "debug"]
    for arg in args:
        if arg not in allowed:
            show_usage_and_exit(f"Invalid arg '{arg}'")

    return args


class ApiError(Exception):
    """Error communicating with Close.com api endpoints"""


class CloseApi:
    """A class managing requests to Close.com api

    Sends requests to an API provided by Close.com for a backend engineering
    job application exercise.
    """

    def __init__(self, url: str = CLOSE_ENDPOINT_URL) -> None:
        """Initialize an instance of an API request manager.

        Args:
            url: a string endpoint URL to send requests to
        """
        self.url = url

    def get_exercise_input(self) -> str:
        """Sends GET request for exercise input data

        Returns:
            Response text string
        """
        try:
            log.info("Sending GET request to '%s'", self.url)

            rsp = httpx.get(self.url)
            rsp.raise_for_status()

            log.debug("Received response text: %s", rsp.text)

            return rsp.text

        except httpx.HTTPStatusError as err:
            raise ApiError(
                f"Invalid status code {err.response.status_code} in response"
            ) from err
        except httpx.RequestError as err:
            raise ApiError("Unexpected request error") from err

    def get_verification_id(self, hashes: list[str]) -> str:
        """Sends POST request to generate Verification ID

        Posts hashed values of the list of traits provided by the exercise
        input data.

        Args:
            hashes: list of strings containing hex digest hash values

        Returns:
            Response text string
        """
        try:
            log.info("Sending POST request to '%s'", self.url)

            rsp = httpx.post(self.url, json=hashes)
            rsp.raise_for_status()

            log.debug("Received response text: %s", rsp.text)

            return rsp.text

        except httpx.HTTPStatusError as err:
            raise ApiError(
                f"Invalid status code {err.response.status_code} in response"
            ) from err
        except httpx.RequestError as err:
            raise ApiError("Unexpected request error") from err


class InputError(Exception):
    """Error related to exercise input data loading and handling"""


class HashingError(Exception):
    """Error related to generating hashed data for verification"""


class VerificationError(Exception):
    """Error related to generation of a Verification ID"""


class ExerciseManager:
    """Close.com application exercise manager

    Encapsulates Close.com exercise data from JSON input encoded as:
    {
        "traits": [ "trait1", "trait2", ... ],
        "key": "key value",
        "meta": {
            "description": "description value"
        }
    }

    Provides hashing function to generated hashed data derived from the
    array of trait strings in the input.

    Manages exercise steps:
        fetching and ingesting input data
        generating hash data
        fetching Verification ID
    """

    def __init__(self, is_test: bool = False) -> None:
        """Initialize ExerciseManager instance

        Initializes internal variables, intantiates an api object.

        Args:
            is_test: bool flag indicates if running in test mode
        """
        self.is_test = is_test
        self.api = CloseApi()
        self.input: str | None = None
        self.traits: list[str] | None = None
        self.key: str | None = None
        self.description: str | None = None
        self._hashes: list[str] | None = None
        self.verification_id: str | None = None

    def load_file(self, fname: str = INPUT_FILENAME) -> str:
        """Load data from a file"""
        log.info(f"Loading data from file '{fname}'")
        with open(fname) as fin:
            data = fin.read()
        return data

    def save_file(self, data: str, fname: str = INPUT_FILENAME):
        """Save data to a file"""
        log.info(f"Saving data to file '{fname}'")
        with open(fname, "w") as fout:
            fout.write(data)

    def load_input(self):
        """Load input data from a source

        Attempts to load JSON encoded data from a source and parse it
        into internal storage.  If is_test is True it attempts to load
        input data from a file, otherwise the api is used to fetch input
        data from the Close.com API endpoint.
        """
        log.info("Loading exercise input data...")

        input: str | None = None

        try:
            if self.is_test:
                input = self.load_file()
            else:
                input = self.api.get_exercise_input()
                self.save_file(input)

            log.debug("Input data: %s", input)

            self.input = input
            decoded = json.loads(input)

            self.traits = decoded["traits"]
            self.key = decoded["key"]
            self.description = decoded["meta"]["description"]

            log.info("Exercise input data loaded.")

        except FileNotFoundError as err:
            raise InputError(
                f"Local input data file not found: '{INPUT_FILENAME}'"
            ) from err
        except ValueError as err:
            raise InputError("Error decoding JSON data") from err

        except KeyError as err:
            raise InputError(
                f"Missing expected key {err} in input data"
            ) from err

    @classmethod
    def hash(cls, data: str, key: str, encoding: str = "utf-8") -> str:
        """Generate a hash value from data and key using blake2 hash function

        Uses standard library hashlib.blake2b hasher to hash the data with
        the provided key.

        Returns:
            Hashed data in a string
        """
        try:
            bkey = key.encode(encoding)
            bdata = data.encode(encoding)
            hasher = blake2b(bdata, key=bkey)
            return hasher.hexdigest()

        except Exception as exc:
            raise HashingError("Unable to generate hash value") from exc

    @property
    def hashes(self) -> list[str]:
        """Returns list of hashed traits"""
        try:
            if not self._hashes:
                assert self.key, "Missing hash key"
                assert self.traits, "Missing traits list"
                self._hashes = [self.hash(t, self.key) for t in self.traits]

            return self._hashes

        except AssertionError as err:
            raise HashingError(
                "Unable to generate hashes, missing input data"
            ) from err

    def get_verification_id(self):

        log.info("Getting Verification ID...")

        try:
            if not self.input:
                raise InputError(
                    "Unable to get verification id, input data missing"
                )

            # acquire verification id data
            data: str | None = None
            if self.is_test:
                data = "Verification ID: test_ver_id"
            else:
                # fetch verfication id response using api
                data = self.api.get_verification_id(self.hashes)

            log.debug("Verification id data: %s", data)

            # expected data looks like: 'Verification ID: nnnnn.xyz'
            if not data.startswith("Verification ID: "):
                raise ValueError(
                    f"Unexpected Verification ID response data: '{data}'"
                )
            self.verification_id = data.split()[-1].strip()

            log.info("Verification ID retrieved.")

        except ApiError as err:
            raise VerificationError(
                "Unable to retrieve Verification ID from API"
            ) from err
        except HashingError as err:
            raise VerificationError(
                "Unable to retrieve Verification ID due to hashing error"
            ) from err
        except InputError as err:
            raise VerificationError(
                "Unable to retrieve Verification ID due to input error"
            ) from err
        except Exception as exc:
            raise VerificationError("Unexpected verification error") from exc

    def show_results(self):
        results = f"""
Close.com application exercise results:

Traits:

{self.traits}

Hash Key:

{self.key}

Description:

{self.description}

Verification ID:

{self.verification_id}
"""
        print(results)

    def run(self):
        self.load_input()
        self.get_verification_id()
        self.show_results()


try:
    is_test = "test" in get_options()
    mgr = ExerciseManager(is_test=is_test)
    mgr.run()

except InputError as err:
    log.exception(err)
except ApiError as err:
    log.exception(err)
except Exception as exc:
    log.exception(exc)
