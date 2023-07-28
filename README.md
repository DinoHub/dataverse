# HaoYi and JinRui's README.md

# Table of Content:

- [Instruction to install DataVerse](#installation)
- [Important Docker Commands](#docker-commands)
- [src Changes](#changes)
    - [lib Folder](#lib)
    - [logic Folder](#logic)
    - [plugins Folder](#plugins)
    - [public Folder](#public)
    - [templates Folder](#templates)
    - [views Folder](#views)
    - [varlibckan Folder](#varlibckan)
- [Extensions](#extensions)
- [Considerations](#considerations)
- [ClearML Configuration](#clearml-config)
- [To Do List](#todo)

---
---

|  Keywords      |  Meaning       |
|----------------|----------------|
|  Project       |  Organization  |
|  Themes        |  Group         |
|  Metadata      |  Package       |
|  Preview       |  Resource      |
|  Credentials   |  ClearML Cred  |
|  Context       |  User Session  |

** Refer to slides to see the structure of Projects & Themes. **

--- 

## Instruction to install DataVerse

Install [Ubuntu](https://apps.microsoft.com/store/detail/ubuntu/9PDXGNCFSCZV) from Microsoft Store. 

Install [Docker](https://docs.docker.com/desktop/install/windows-install/).

Open Docker Desktop.  It may prompt you to run wsl --update on cmd / powershell. (if you run this step, you will be able to use docker commands on cmd or powershell)

To enable Docker to be accessed via Ubuntu command line:
- Open Settings > Resources > Enable integration with Ubuntu
- Restart Docker desktop (Right click icon and restart)

Git clone the [DataVerse Repository](https://github.com/ghy99/DataVerse) from ghy99 github.

Open Ubuntu Terminal and navigate to where the cloned repository is stored.

Run the following commands:

Build the docker image:
```
docker compose -f docker-compose.dev.yml up --build
```

List the containers:
```
docker ps -a
```

Ensure that clearml is inside the `dev-requirements.txt` file.


When the status of the container is `(healthy)`, enter the container to create ClearML Credentials:
```
docker exec -it <container ID> /bin/sh

clearml-init
```

Copy and paste your ClearML credentials.

Restart your docker container.

---

## Important Docker Commands: <a id="docker-commands"></a>

Build docker container:
```
docker compose -f docker-compose.dev.yml up --build
```

Copy files from Docker: ( I think is smth like that ah )
```
docker cp <container id>:<filepath> <destination>
```

List docker containers:
```
docker ps -a
watch docker ps -a
```

Delete docker containers:
```
docker rm $(docker ps -a -q)
```

Delete docker images:
```
docker rmi $(docker images)
```

---

## Things that we added / changed in the `srv/app/src` folder: <a id="changes"></a>

We copied out the main folders from the ckan-dev container such as:
- `/lib`
- `/logic`
- `/plugins`
- `/public`
- `/templates`
- `/views`
- `/var/lib/ckan`

---

### lib Folder: <a id="lib"></a>

This folder contains all the built in functions that CKAN created. 

Important ones that we looked through:
- `helpers.py`
- `datapreview.py`
- `uploader.py`

> `datapreview.py` was edited by us (Hao Yi) as there seemed to be a bug inside.
>
> `datapreview.py` is called to check for default view types. 
>
> This is used to show a preview of the file that is uploaded for previews / resources.
>
> Under `get_default_view_plugins()` function, it checks the list of view types that are declared in `ckan.ini`
> The default types are `text_view` and `datatables_view`.
> However, I changed it through the `.env` file. 
>
> When changed, it only takes in a string when retrieving the new view types from the `.env` file. 
>
> I changed the function to check the type of config value retrieved from the `.env` file.
> If it is a string, I convert it to a list so that CKAN can process it as an actual view type instead of looping through a string. 
>
> The extensions `audio_view`, `datatables_view`, `image_view`, `text_view`, `video_view` are the current available view types for the resource page. 
>
>> Extension `text_view` currently has a `BUG` where it is not loading my css file changes.
>> Original `text_view` code is overriding my CSS changes to change the font colour to white. Currently the font colour is black so cannot see on screen.

---

### logic Folder <a id="logic"></a>

This folder stores the API functions, authorization functions and a few other scripts.

Important ones that we looked through:
- `/action/create.py`
- `/action/delete.py`
- `/action/get.py`
- `/action/patch.py`
- `/action/update.py`

For each API function, they would require an authorization check. Each function will call `_check_access()` which calls the `/auth/` folder to check if the current user is allowed to perform certain API action. 
- All API function requires 2 parameters, `context` and `data_dict`. 
- `context`: Stores information on the current user session that is logged in. Using the current session, `/auth/<action>.py` will check the user's permissions to check if they can perform this action.
    - Usually, we just pass in an empty dictionary as CKAN will retrieve the current session automatically through their `/auth/<action>.py`.
    - If you want to overwrite current session, can just pass in admin rights in the `context` parameter. 
- `data_dict`: This dictionary contains the form that user submits. 
    - For example, user wants to create a package. 
    - This form will be converted into a dictionary after submitting in the front-end, and stored inside `data_dict`. 
    - This dictionary will then be passed into the API function `package_create`, and the package will be created and stored inside the CKAN database. 


** Do read through CKAN Documentation to figure out how the API works **

--- 
### plugins Folder <a id="plugins"></a>

This folder stores files like the plugin interfaces and toolkit.

Important ones that we looked through:
- [`interfaces.py`](https://docs.ckan.org/en/2.10/extensions/plugin-interfaces.html)
- [`toolkit.py`](https://docs.ckan.org/en/2.10/extensions/plugins-toolkit.html)

`interfaces.py` contains core classes and functions that plugins implement. 
- E.g. To implement IDatasetForm, refer to `/src/ckanext-datasetform/ckanext/datasetform/plugin.py`.

---

### public Folder <a id="public"></a>

This folder stores all the front end code, such as css files, images, javascript files, and the bootstrap and jquery files.

Important files that we added / edited:
- `/css/main.css`
- `/images/dataverse-logo-footer.png`
- `/images/dataverse-logo.png`

> We modified the front end designs through /css/main.css.
> (The gorgeous design rn).
>
>We also added our own logo for the header.html and footer.html.

---

### templates Folder <a id="templates"></a>

This folder stores all the html files rendered in the frontend. 

Important files that we looked through:
- `/home`
- `/macros`
- `/package`
- `/snippets`
- `footer.html`
- `header.html`
- `page.html`
- `base.html`

> The files that we overwrote are all stored inside the `datasetform` extension (file path:dataverse\src\ckanext-datasetform\ckanext\datasetform\templates) .
>
> Did not change many files here as we added our own templates to overwrite the original.

---

### views Folder <a id="views"></a>

This folder stores the python scripts that handle the flask requests that occurs during usage. 

All `POST` and `GET` requests done in the front-end goes through the scripts in the `views` folder.

- E.g. Creating metadata (package) process:
    - User selects `Add Dataset` button.

    - Flask checks the action request, and adds the package type to the request. In this case, the package type is `'dataset'`. 
        - Refer to IDatasetForm `package_type()` function for the used package type in DataVerse. 

    - This action performs a `GET` request to flask through the `'<package_type>/new'` URL request.

    - Flask looks through its blueprint for a `'/dataset/new` URL. 

    - Flask checks one of the helper functions inside `/lib` folder, refer to `/lib/plugins.py`.
        - Refer to `register_package_blueprints()` function. This is where CKAN checks for existing extensions that added its own blueprint for the `/dataset/new` URL.

    - If there is no added blueprints in extensions, it will go to the next step.
        - This blueprint is located in `views/dataset.py`.
            - Refer to the `register_dataset_plugin_rules()` function at the bottom of the script.
            - Refer to the `dataset` variable which is a Blueprint Object at the top of the script. 

    - If there is an added blueprint in extensions, it will register the extension's plugin. 
        - Refer to the `README.md` in the extension `datasetform`.
        - Refer to `/src/ckanext-datasetform/ckanext/datasetform/plugin.py`.
        - Refer to `register_package_blueprints()` function in `plugin.py`.
        - We added a URL rule to overwrite the `'/dataset/new'` URL. 

    - Refer to the `view_func` parameter. This parameter tells flask where to look for the `POST`/`GET` request method. 

    - Flask runs the function for `GET` in this scenario. 

    - This function processes the logic to render HTML for the `'/dataset/new'` URL.

    - This is the end of this process to `GET` the `'/dataset/new'` URL. 
    

Important files that we looked through:
- `dataset.py`
- `resource.py`

> We edited `resource.py` as our script to overwrite `resource.py` did not work for some reason. 
>
> Unsure why CKAN did not register our own blueprint for `resource.py`.
> 
> Refer to `datasetform` extension under `views.py`, and `plugins.py`. 
>> We added the `prepare_resource_blueprint()` function and it shows that it added our blueprint, but it just did not load our URL.
>>
>> So we just overwrote the original `resource.py` file.
>
> We also added our own function `upload_to_clearml()` to handle the dataset uploading to ClearML.
> 
> The function that we overwrote in `resource.py` is the `post()` function in the class `CreateView`.
> 
>> We changed it such that it will download and store the files uploaded in the docker container, then upload it to ClearML. 
>>
>> After uploading, we call the `change_dataset_title()` function to change the name of our dataset in DataVerse. 
>>
>> Lastly, we will delete the files that are uploaded to save space in the docker container.

### /var/lib/ckan Folder <a id="varlibckan"></a>

This folder stores the uploaded resources to DataVerse. 

In Dataverse, all files that are meant to be uploaded to ClearML is stored inside a temporary folder inside `/var/lib/ckan`.

For example, resource files are stored the /resources folder. The names of the files are changed to the resource ID, split by the names in the order of:
    
    [0:3] : first folder
    [3:6] : second folder
    [6: ] : file

- Current files stored inside the `/resources` folder are all previews that are uploaded for datasets.
- Current files stored inside `/storage/uploads/group` stores all group profile images uploaded.
- Current files stored inside `/storage/uploads/user` stores all user profile images uploaded.

> Files that will be uploaded to ClearML are stored in a `/default` folder, which will be deleted after the upload is complete. 

---

## Extensions <a id="extensions"></a>

List of extensions:
- `audio_view`
- `datatables_view`
- `image_view`
- `text_view`
- `video_view`
- `datasetform`
- `fileuploader`
- `packagecontroller`
- `resourcecontroller`
- `versiontree`

***Please refer to their own README in the extensions.***


## Things to note: <a id="considerations"></a>

- When there is any changes to the .env file or the docker-compose.dev.yml file, the docker container ckan-dev will be recreated. So any files added through "`docker exec -it <container id> /bin/sh`" will be deleted. 
    - For example, the ClearML credentials that we added when we ran the clearml-init command will be deleted. 
- To retrieve data from the `ckan.ini` file, add the following code.
    ```
    import toolkit
    variable = toolkit.config.get(<some variable in ckan.ini>)
    ```

## ClearML Configuration: <a id="clearml-config"></a>

- Currently, our ClearML credentials are hardcoded, such that we have to call "`docker exec -it <container id> /bin/sh`" to enter the container can create our ClearML credentials inside before we can create any datasets that will be stored in ClearML. 

### Steps to create ClearML credentials:

> Add `clearml` in dev-requirements.txt
>
> Our current one is added inside resourcecontroller extension.
>
> Navigate to the folder where `docker-compose.dev.yml` is stored.
>
> Run the following command to bring the docker container up:
>>`docker compose -f docker-compose.dev.yml up --build`
>
> Enter the ckan-dev docker container by running the command in a Ubuntu terminal:
>
>> `docker exec -it <container id> /bin/sh`
>
> Run the following command to start the initialization process:
>> `clearml-init`
>
> Switch to the /root folder:
>> `cd /root`
>
> Run the following command to copy the `clearml.conf` file into the /srv/app folder where CKAN is running:
>> `cp clearml.conf /srv/app`
>
> Exit the docker container by typing `ctrl + d`.
>
> Down the docker by typing `ctrl + c`.
>
> Up the docker container again. 

## DataVerse Databases:

To access the databases, follow the following instructions:

> Navigate to the folder where `docker-compose.dev.yml` is stored.
>
> Run the following command to bring the docker container up:
>>`docker compose -f docker-compose.dev.yml up --build`
>
> Enter the db docker container by running the command in a Ubuntu terminal:
>
>> `docker exec -it <container id> /bin/sh`
>
> Enter the following command to log in:
>> `psql -U ckan -d ckan`
>
> Enter the following command to list all tables:
>> `\dt`
>
> To query the database, use postgresql queries. 
>
> E.g.: To select everything from table `package`:
>> `select * from "package";`

# To Do after Alpha Version: <a id="todo"></a>

- [x] Fix `Edit Datasets`. Allow Users to edit datasets without bugs. (Currently, editing metadata works, but there are some empty fields for some reason not sure why, and we are not sure if we edit the resources, it will affect clearml side or not)
    - [x] Unable to create datasets of the same name as it will crash, which results in being unable to "add" new versions of the dataset. Have to do it through edit which will in turn update the dataset with a new version in ClearML. This will be under Edit Dataset as technically its a new version of the dataset. If edit, it is supposed to create a new dataset in ClearML with a new version under the same project and dataset title. 
- [x] Fix `Delete Datasets`. Allow Users to delete datasets without bugs, including on the ClearML side. 
- [ ] Add ClearML credentials to the `Register Account`. Users should upload their ClearML credentials so that DataVerse has access to their ClearML account. 
- [ ] Send credentials along with ClearML Dataset requests to communicate with ClearML servers. Currently rely on `clearml.conf` to establish connection to ClearML. Not feasible when introducing multiple users. 
- [ ] Improve version tree design, as well as add more information for user to view in version tree, such as metadata details and links to dataset in DataVerse. 
- [ ] Allow multiple dataset selection and manipulation. 
- [ ] Add CSRF Token to allow removal of dataset from groups.
- [ ] Add a loading screen while uploading datasets to ClearML (There is a long buffer for some reason).
- [ ] Prevent the `Download` button from being available to all users. Should only be available to users who are in the same project as the dataset. 
- [ ] Assign access to people who request for dataset download.
    - [ ] Show them who the Point Of Contact is when they want to download the dataset.
    - [ ] Allow users to request to dataset owners for permissions to download the dataset. 
- [ ] Add a loading screen when dataset is being created / deleted. Currently it takes too long and theres no loading screen.
