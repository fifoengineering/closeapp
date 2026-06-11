# Close.com application exercise

A script to retrieve a Verification ID for submission with a close.com job application.

## Usage

The following was written for a linux development environment and depends on `git`, `uv` and `python`.  The instructions in this document were tested with these versions:

- `git 2.43.0`
- `uv 0.11.14`
- `python 3.13.3`

To install and run (assuming `git` and `uv` are installed):

```bash
$ git clone git@github.com:fifoengineering/closeapp.git closeapp
$ cd closeapp
$ uv run exercise.py
```

The log level is set to `error` by default but can be adjusted by adding `--debug` as a command line argument when running the script, e.g. `uv run exercise.py --debug`

### Dependencies

The script uses `httpx` to access the Close.com API.  Testing depends on `pytest`, `pytest-mock`, `pytest-httpx` and `coverage`.  You'll need to activeate the project virtual environment if you want to use the testing tools:

```bash
$ source ./.venv/bin/activate
```

## Testing

The project includes unit tests:

```bash
$ pytest
```

You can use the `coverage` tool to determine code coverage:

```bash
$ coverage run -m pytest
$ coverage report -m

```

