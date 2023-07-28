[Refer to HaoYi's GitHub for DataVerse for reference i guess](https://github.com/ghy99/DataVerse)

# ckanext-text_view

This extension is used to display text previews in datasets. When a user uploads a text file for the preview, this extension is used to display the text div so that the preview can be played. 
*taken from github's ckan/ckan under src_extensions.

- This extension currently has a bug.
- I am unable to overwrite the default text_view that renders text resources. 
- Tried changing my CSS and register my extension inside the `.env` file, but CKAN is still taking the default value from the original `text_view`. 
- I could not find the original code for `text_view` as well. 

## Installation

1. Create an extension with the following command:
   
   `docker compose -f docker-compose.dev.yml exec ckan-dev /bin/sh -c "ckan generate extension --output-dir /srv/app/src_extensions"`

2. Add your extension name to your .env file. 

   `CKAN__PLUGINS="envvars text_view"`
   `CKAN__VIEWS__DEFAULT_VIEWS=<extension name> (separated by space)`

3. Restart CKAN. 

   `docker compose -f docker-compose.dev.yml up --build`

* There is a bug in lib/datapreview.py at line 131.
The string taken from the .env file was not processed, resulting in CKAN being unable to process all added view plugins. I modified the original code here to convert the string into a list to process the default view types.


## Config settings

[refer to  Installation.](#installation)

## Tests

** Not done yet. No tests written. **

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
