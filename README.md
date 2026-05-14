# Close.com application exercise

A script to retrieve a Verification ID to submit with a close.com job application.

## Usage

The following was written for a linux development environment and depends on `git`, `uv` and `python`.  The instructions in this document were tested with these versions:

- git 2.43.0
- uv 0.11.14
- python 3.13.3

To install and run:

```bash
$ cd ~/<project directory path>
$ git clone git@github.com:fifoengineering/closeapp.git closeapp
$ cd closeapp
$ uv run exercise.py
```

The log level is set to `error` by default but can be adjusted by adding `info` or `debug` as command line args when running the script, e.g. `uv run exercise.py info`

### Dependencies

The script uses `httpx` to access the Close.com API.

### Testing

The project includes unit tests.

```bash
$ pytest

```