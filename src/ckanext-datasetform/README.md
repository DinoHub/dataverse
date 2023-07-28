[Refer to HaoYi's GitHub for DataVerse for reference i guess](https://github.com/ghy99/DataVerse)

# ckanext-datasetform

This extension is used to modify the package and resource creation form. 

>The HTML files written by us to overwrite the original are also stored in this extension. 
>>The modified HTML files are stored in templates. 
>>It is mostly a reflection of the files stored in /templates. 
>>The modifications mostly overwrite the {% block %} from the original HTML files. 

    
**views.py**
    This plugin contains the classes that are used to overwrite the package / resource creation process. Classes are copied from different .py files in the views folder into this views.py file. Then plugin.py file imports these classes from views.py file.
```python
    '''
    Most of the functions in here are directly copied from views/dataset.py and views/resource.py to ensure that the classes would work properly.

    We will only explain the functions that we added ourselves. 
    '''

    upload_to_clearml(folderpath, package_id, project_title, dataset_title, parent_datasets)
    '''
    This function is used to upload the uploaded files to ClearML. 
    `folderpath` is passed in as the files that are uploaded are stored inside the docker container in the filepath `folderpath`. We then upload the files by specifying the filepath for ClearML to retrieve and upload to the server. 

    `package_id` is not used idk why i passed it in. I thought it was necessary. 

    `project_title` is the project title used to create the project in ClearML. 

    `dataset_title` is the dataset title used to create the dataset in ClearML. 

    `parent_datasets` are IDs of datasets that the newly created dataset will inherit from. 
    '''

    add_groups(pkg_dict)
    '''
    This function is used to check if `subject_tags` exists in pkg_dict, parse through its value and add each value into `groups` in pkg_dict. 
    Then using ckan_admin privileges, force add the datasets into the groups (themes).
    '''

    class CreatePackageView(MethodView):
        post(self, package_type)
        '''
        I will explain what we changed from the original `post` function from dataset.py.

        We requested for the file uploaded for the preview parameter and created a resource for this preview. 
        This is necessary to allow users to see the uploaded preview that is used to describe the dataset.

        I added a portion at line 132 that checks for `subject_tags`. 
        This is to check for the additional `themes` that the user would want this dataset to be added to. 
        However, I used the default sysadmin credentials to override adding the dataset to groups (themes) as I could not use IAuthFunction to override that process. 
        ** Pls change that part. **

        We also removed the check for `create_on_ui_requires_resources`, instead referring to the parameter `new_or_existing` passed in through `pkg_dict`.
        This is used to differentiate between adding a new dataset and referencing an old dataset from ClearML. 
        '''

        get(self, package_type, data, errors, error_summary)
        '''
        I added a portion at line 488, where i retrieved the current existing group list and passed it in as groupList.
        This is for the package form that will display all the groups that user will want to add the current dataset into.
        '''

    class CreateResourceView(MethodView):
    '''
    This is not being used. I could not overwrite the original with this as it gave me some issues about being unable to overwrite existing URL points. 

    This class is supposed to overwrite the resource form creation portion, but it is not being called. What it is supposed to do is:

        Store the uploaded files from the resource form in the folder path `/var/lib/ckan/default`.

        When the uploaded files are stored here, we will call the `upload_to_clearml` function to upload the files to ClearML. 

        After the upload, we will then delete the uploaded files to reduce space wastage. 
    '''

    edit_groups(pkg_dict)
    '''
    This function is used to check if `subject_tags` exists in pkg_dict, parse through its value and add each value into `groups` in pkg_dict. 
    Then using ckan_admin privileges, force add the datasets into the groups (themes).
    '''

    class EditPackageView(MethodView):
        post(self, package_type)
        '''
        I will explain what we changed from the original `post` function from dataset.py.
        Instead of using package_update, i swapped it with package_patch.
        package_update was causing form inputs that were not filled in to be deleted. 

        We also allowed users to add more groups through the edit form, and add new resources for preview.
        '''

        get(self, package_type, data, errors, error_summary)
        '''
        I retrieved the current existing group list and passed it in as groupList.
        This is for the package form that will display all the groups that user will want to add the current dataset into.

        '''

    deleteClearML(package_id)
    '''
    This function is used to delete the dataset on ClearML side.
    '''

    class DeleteView(MethodView):
    '''
    This class is used to purge datasets. 
    '''
        post(self, package_type)
        '''
            I will explain what we changed from the original `post` function from dataset.py.
            Instead of using `package_delete` to just change the status of the dataset from active to deleted, we use `dataset_purge` to delete the dataset completely. 
            This action of deleting the dataset cannot be undone. 
        '''
```

**plugin.py:**
    This plugin mainly uses the IDatasetForm Interface. There are 8 main functions used in IDatasetForm.
```python
    prepare_dataset_blueprint(self, package_type, bp)
    '''
    We added a url rule to the blueprint `bp` to overwrite the package creation process. 
    This new rule will call the Class CreatePackageView from views.py. 
    '''

    prepare_resource_blueprint(self, package_type, blueprint)
    '''
    We added a url rule to the blueprint `blueprint` to overwrite the resource creation.
    However, this does not work for some reason even though the steps were exactly the same as in prepare_dataset_blueprint. 
    Mira was unsure of what happened here too. 
    Might have to fix this. 
    We overwrote the original /views/resource.py code instead. 

    **fix this**
    '''

    _modify_package_schema(self, schema)
    '''
    This function is a helper function to consolidate all the additional parameters that we added into package schema. 
    Each key in schema.update is a form input from package form (Dataset creation).
    
    `toolkit.get_converter('convert_to_extras')` is added to a list of checklist that CKAN checks before storing it in the database. 
    This parameter ensures that all added form inputs will be stored inside the `extras` table.

    `toolkit.get_validator("ignore_missing")` is added to a list of checklist that CKAN checks before storing it in the database. 
    This parameter is added when the form input is not compulsory. 

    As we did not add any new form inputs in the resource form, we did not need to cast the schema to ['resources'] to store data in the resource table. 
    Please refer to the commented line of code in line 177 - 184 for an example of how to cast to the resource form. 
    '''

    create_package_schema(self)
    '''
    This function creates the schema and calls _modify_package_schema() to store values in the database.
    '''

    update_package_schema(self)
    '''
    This function updates the schema and calls _modify_package_schema() to update values in the database.
    '''

    show_package_schema(self)
    '''
    This function retrieves data stored in the database. 
    `toolkit.get_converter("convert_from_extras)` is added to convert data from the `extras` parameter to a key : value pair data_dict.
    '''

    is_fallback(self)
    '''
    If true, this IDatasetForm plugin will be used as the default handler for package types that are not handled by any other IDatasetForm plugin. 

    Refer to package_types() function below.
    '''

    package_types(self)
    '''
    This function is used to specify what package types this plugin will handle. 
    "dataset" is returned in this plugin, specifying that all `dataset` package types will be handled by this plugin. 

    However, for some reason, the resource form does not enter here but goes to the original default resource form. Not sure why this is happening. 
    
    **fix this**
    '''
```

## Installation

1. Create an extension with the following command:
   
   `docker compose -f docker-compose.dev.yml exec ckan-dev /bin/sh -c "ckan generate extension --output-dir /srv/app/src_extensions"`

2. Add your extension name to your .env file. 

   `CKAN__PLUGINS="envvars datastore datapusher datasetform"`

3. Restart CKAN. 

   `docker compose -f docker-compose.dev.yml up --build`


## Config settings

None at present


## Tests

None at present
