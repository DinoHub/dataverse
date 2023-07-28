[![Tests](https://github.com/ghy99/ckanext-iauthfunction/workflows/Tests/badge.svg?branch=main)](https://github.com/ghy99/ckanext-iauthfunction/actions)

# ckanext-iauthfunction

This extension is currently not used.

## Installation

1. Create an extension with the following command:
   
   `docker compose -f docker-compose.dev.yml exec ckan-dev /bin/sh -c "ckan generate extension --output-dir /srv/app/src_extensions"`

2. Add your extension name to your .env file. 

   `CKAN__PLUGINS="envvars iauthfunction"`

3. Restart CKAN. 

   `docker compose -f docker-compose.dev.yml up --build`


## Config settings

None at present

[refer to  Installation.](#installation)


## Developer installation

To install ckanext-iauthfunction for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/ghy99/ckanext-iauthfunction.git
    cd ckanext-iauthfunction
    python setup.py develop
    pip install -r dev-requirements.txt

## Tests

** Not done yet. No tests written. **

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)