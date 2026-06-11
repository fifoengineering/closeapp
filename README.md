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

Close.com application code exercise

INPUT

Description
-----------
Enclosed are some traits that [Joe](https://www.linkedin.com/in/jkemp101/) believes great engineers exhibit. Using the included UTF-8 `key`, construct a JSON array using the lowercase hex digest of the blake2b hash for each trait (digest size=64). POST this bare array back to this endpoint. Example array: ["1f9ec19c7...57fd27e5", "79c72b47088...bf13026c", ...] If the hashes are correct you will get a Verification ID you should include in your application. 400 responses indicate a problem with the hashes in your array. Note, the key rotates each day around midnight EST.

Traits
------
Craftsman, Pragmatic, Curious, Methodical, Driven, Collaborator

Key
---
Close-123abcd4

OUTPUT

Hashed Traits
-------------
"428deee038cd78ec7a29c7a84123f399cf127d5d5e1b3a9142be531086e15146fe5640d0bc7729ce23e8a4861ba24a1dac3ad40aa2b91af0a4bf77ef92df678d", "372cbea6f26bb49da115e1020f1dea20e0b4818e9dd975d73387f3269903e3f6b9bcb1a169945cdc6a9c52eb78fe6e126ff752a8a0f49e49f66a87660d564b14", "8e090d2297a2f983eceb364e3fa1c3ca62ff05935a957f37264d291dc27ee80e3091b7c9c79825ea65465ec4e1ae721fb4245660e87fc9712810985104ae9702", "0e310bf02d0a53caa76e21abb0bc94beedf1b2b021de25a36788123c3b053f9d498bf292f5d4c5bff8a6846591cf9da52f65b12c482627f79c832cda7f2e3afa", "1ab971e78e0bc7a5fd48a98235f879cf7b8e1b319e22c04e5b771b5ffc80f32a85df1c938865cd6b38aeffbd77c01e79e66f2e5da1014665b88b71611ad3bb92", "71d54ea64f878389b07fae2a517dfd8bc4c7fb1b8f73f8cb1e8d6c7ac94043463a9026cf47b3890d99701cd08aea329cce192ec0183176752149aaf8f7eab8f9"

Verification ID
---------------
1781198062.sTA2hTfSQQM

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

