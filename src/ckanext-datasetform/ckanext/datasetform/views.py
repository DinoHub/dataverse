# encoding: utf-8
from __future__ import annotations

import logging
import inspect
from typing import Any, Optional, Union, cast

import cgi
from flask.views import MethodView
from ckan.common import current_user

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckan.views.home import CACHE_PARAMETERS
from ckan.lib.plugins import lookup_package_plugin
from ckan.lib.search import SearchIndexError
from ckan.types import Context, Response
import ckan.plugins.toolkit as toolkit

import os
import shutil
from werkzeug.datastructures import FileStorage
from clearml import Dataset
import hashlib

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

log = logging.getLogger(__name__)


def _setup_template_variables(
    context: Context, data_dict: dict[str, Any], package_type: Optional[str] = None
) -> None:
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def _get_pkg_template(template_type: str, package_type: Optional[str] = None) -> str:
    pkg_plugin = lookup_package_plugin(package_type)
    method = getattr(pkg_plugin, template_type)
    signature = inspect.signature(method)
    if len(signature.parameters):
        return method(package_type)
    else:
        return method()


def _tag_string_to_list(tag_string: str) -> list[dict[str, str]]:
    """This is used to change tags from a sting to a list of dicts."""
    out: list[dict[str, str]] = []
    for tag in tag_string.split(","):
        tag = tag.strip()
        if tag:
            out.append({"name": tag, "state": "active"})
    return out


def _form_save_redirect(
    pkg_name: str, action: str, package_type: Optional[str] = None
) -> Response:
    """This redirects the user to the CKAN package/read page,
    unless there is request parameter giving an alternate location,
    perhaps an external website.
    @param pkg_name - Name of the package just edited
    @param action - What the action of the edit was
    """
    assert action in ("new", "edit")
    url = request.args.get("return_to") or config.get("package_%s_return_url" % action)
    if url:
        url = url.replace("<NAME>", pkg_name)
    else:
        if not package_type:
            package_type = "dataset"
        url = h.url_for("{0}.read".format(package_type), id=pkg_name)
    return h.redirect_to(url)


def _get_package_type(id: str) -> str:
    """
    Given the id of a package this method will return the type of the
    package, or 'dataset' if no type is currently set
    """
    pkg = model.Package.get(id)
    if pkg:
        return pkg.type or "dataset"
    return "dataset"


def upload_to_clearml(
    folderpath, package_id, project_title, dataset_title, parent_datasets
):
    logging.warning(f"Package ID: {package_id}")
    logging.warning(f"Folder Path: {folderpath}")
    logging.warning(f"Project Title: {project_title}")
    logging.warning(f"Dataset Title: {dataset_title}")
    logging.warning(f"Parent Datasets: {parent_datasets}")
    if parent_datasets:
        dataset = Dataset.get(
            dataset_project=project_title,
            dataset_name=dataset_title,
            parent_datasets=parent_datasets,
            auto_create=True,
        )
    else:
        dataset = Dataset.get(
            dataset_project=project_title, dataset_name=dataset_title, auto_create=True
        )

    logging.warning(f"----------ADDING FILES TO DATASET----------")
    dataset.add_files(path=r"{}".format(folderpath))
    logging.warning(f"----------UPLOADING TO CLEARML----------")
    dataset.upload(show_progress=True, verbose=True)
    logging.warning(f"----------FINALIZING DATASET----------")
    # if resource_show['save'] =='go-metadata':
    dataset.finalize(verbose=True, raise_on_error=True, auto_upload=True)
    return dataset.id


def add_groups(pkg_dict):
    if "subject_tags" in pkg_dict:
        logging.warning(f"________________*********************** {pkg_dict['subject_tags']}")
        if isinstance(pkg_dict['subject_tags'], str):
            pkg_dict['subject_tags'] = pkg_dict['subject_tags'].strip("{}")
            pkg_dict['subject_tags'] = pkg_dict['subject_tags'].split(',')
        # logging.warning(f"****************** SUBJECT TAGS:")
        # logging.warning(f"\t\t __** TAG: {pkg_dict['subject_tags']}")
        groups_list = []
        for groupname in pkg_dict['subject_tags']:
            groups_list.append({
                'name' : groupname
            })
        pkg_dict['groups'] = groups_list
        del pkg_dict['subject_tags']

        for key, val in pkg_dict.items():
            logging.warning(f"******* {key} : {val}")
        admin = toolkit.config.get("ckan_sysadmin_name")
        password = toolkit.config.get("ckan_sysadmin_password")

        logging.warning(f"*^_*^_*^_*^_ ADMIN: {admin}, PASSWORD: {password}")

        pkg_dict = get_action("package_patch")({
            # "ignore_auth" : True,
            'user' : admin,
            'password' : password,
        }, pkg_dict)

        for key, val in pkg_dict.items():
            logging.warning(f"*******_____________ {key} : {val}")
    return pkg_dict


# dataset.py
# For Package Form
class CreatePackageView(MethodView):
    def _is_save(self) -> bool:
        return "save" in request.form

    def _prepare(self) -> Context:  # noqa
        context = cast(
            Context,
            {
                "model": model,
                "session": model.Session,
                "user": current_user.name,
                "auth_user_obj": current_user,
                "save": self._is_save(),
            },
        )
        try:
            check_access("package_create", context)
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to create a package"))
        return context

    def post(self, package_type: str) -> Union[Response, str]:
        """
        This function is called when user submits the package form when creating datasets.
        What we did here was to request for uploaded files when user uploads a preview for the dataset.
        Then, we create a resource for the preview file so that users can see the preview file when it is created.

        Args:
            package_type (str): This refers to the package type e.g. dataset.
                                Can refer to plugins.py function package_types.
                                It returns a list of package types that will pass through this class when that package type is called.
        """
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        context = self._prepare()
        is_an_update = False
        ckan_phase = request.form.get("_ckan_phase")
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
            files = dict_fns.unflatten(tuplize_dict(parse_params(request.files)))

            logging.warning(f"-- ---- ---- VIEWS.py ---------- PACKAGE FORM UPLOADING ")
            logging.warning(f"-- ---- ---- FILES: {files} ----------------------------")
            data_dict.update(clean_dict(files))
        except dict_fns.DataError:
            return base.abort(400, _("Integrity Error"))
        # validate ClearML ID for referencing existing dataset
        if data_dict["new_or_existing"] == "Reference Existing Dataset":
            try:
                dataset = Dataset.get(dataset_id=data_dict["clearml_id"])
            except Exception as e:
                return base.abort(404, _("ClearML ID not found"))

        # logging.warning(f"_*^_*^_*^ Data Dict: ")
        # for key, val in data_dict.items():
        #     logging.warning(f"{key} : {val}")
        org_name = get_action("organization_show")({}, {"id" : data_dict['owner_org']})
        logging.warning(f"_*^_*^_*^_*^_*^ ORGANIZATION NAME: {org_name['name']}")
        data_dict['project_title'] = org_name['title']
        logging.warning(f"_*^_*^_*^_*^_*^_*^ PROJECT TITLE: {data_dict['project_title']}")

        # Converting project and dataset title to lowercase
        data_dict['project_title'] = data_dict['project_title'].lower()
        data_dict['dataset_title'] = data_dict['dataset_title'].lower()


        check_clearml = None
        try:
            check_clearml = Dataset.get(
                dataset_project=data_dict['project_title'],
                dataset_name=data_dict['dataset_title']
            )
        except Exception as e:
            logging.warning(f"IT DOES NOT EXIST {e}")


        new_name = None
        if check_clearml == None:
            new_name = data_dict['dataset_title'] + "_v1-0-0"
        else:
            ver = check_clearml._dataset_version.split(".")
            ver[-1] = str(int(ver[-1]) + 1)
            version = '.'.join(ver)
            new_name = check_clearml.name + version
            
        new_name = new_name.replace(" ", "-")
        new_name = new_name.replace(".", "-")
        new_name = new_name.lower()


        logging.warning(f"_*^_*^_*^ CHECK NEW NAME: {new_name}")

        # Making data_dict["name"] into a gibberish
        # sha_hash = hashlib.sha256()
        # newname = data_dict['name'].encode('utf-8')
        # sha_hash.update(newname)
        # encoded_name = sha_hash.hexdigest()
        
        data_dict['name'] = new_name
        logging.warning(f"__**^^__**^^__**^^ We reached hereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        for key, val in data_dict.items():
            logging.warning(f"__^^__^^__^^__**__**__** {key} : {val}")

        try:
            if ckan_phase:
                # prevent clearing of groups etc
                context["allow_partial_update"] = True
                # sort the tags
                if "tag_string" in data_dict:
                    data_dict["tags"] = _tag_string_to_list(data_dict["tag_string"])
                if data_dict.get("pkg_name"):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict["id"] = data_dict["pkg_name"]
                    del data_dict["pkg_name"]
                    # don't change the dataset state
                    data_dict["state"] = "draft"
                    # this is actually an edit not a save
                    pkg_dict = get_action("package_update")(context, data_dict)
                    # redirect to add dataset resources
                    url = h.url_for(
                        "{}_resource.new".format(package_type), id=pkg_dict["name"]
                    )
                    return h.redirect_to(url)
                # Make sure we don't index this dataset
                if request.form["save"] not in ["go-resource", "go-metadata"]:
                    data_dict["state"] = "draft"
                # allow the state to be changed
                context["allow_state_change"] = True

            data_dict["type"] = package_type

            pkg_dict = get_action("package_create")(context, data_dict)

            # ADDING THIS LINE TO PARSE "SUBJECT_TAGS"
            # THIS PART I FORCE AUTHORIZE ADD TO GROUP USING ADMIN CREDENTIALS... PLS CHANGE THIS PART
            pkg_dict = add_groups(pkg_dict)
            # if "subject_tags" in pkg_dict:
            #     pkg_dict['subject_tags'] = pkg_dict['subject_tags'].strip("{}")
            #     pkg_dict['subject_tags'] = pkg_dict['subject_tags'].split(',')
            #     # logging.warning(f"****************** SUBJECT TAGS:")
            #     # logging.warning(f"\t\t __** TAG: {pkg_dict['subject_tags']}")
            #     groups_list = []
            #     for groupname in pkg_dict['subject_tags']:
            #         groups_list.append({
            #             'name' : groupname
            #         })
            #     pkg_dict['groups'] = groups_list
            #     del pkg_dict['subject_tags']

            #     for key, val in pkg_dict.items():
            #         logging.warning(f"******* {key} : {val}")
            #     admin = toolkit.config.get("ckan_sysadmin_name")
            #     password = toolkit.config.get("ckan_sysadmin_password")

            #     logging.warning(f"*^_*^_*^_*^_ ADMIN: {admin}, PASSWORD: {password}")

            #     pkg_dict = get_action("package_update")({
            #         # "ignore_auth" : True,
            #         'user' : admin,
            #         'password' : password,
            #     }, pkg_dict)

            #     for key, val in pkg_dict.items():
            #         logging.warning(f"*******_____________ {key} : {val}")

            logging.warning(
                f"PRINTING THE LATEST PACKAGE DICT AFTER UPDATE, BEFORE I CREATE A RESOURCE"
            )
            # for key, val in pkg_dict.items():
            #     logging.warning(f"-- -- __ __ {key} : {val}")
            logging.warning(" ")
            logging.warning(" ")    
            if data_dict['upload']:
                resource = get_action(f"resource_create")(
                    {},
                    {
                        "package_id": pkg_dict["id"],
                        "upload": data_dict["upload"],
                        "preview": True,
                        "format": "",
                    },
                )

                pkg_dict["resources"].append(resource)
                pkg_dict = get_action("package_update")({}, pkg_dict)

            # logging.warning(f"IM GONNA PRINT THE RESOURCE FROM THE PACKAGE DICT ABOVE:")
            # for resource in pkg_dict["resources"]:
            #     for key, val in resource.items():
            #         logging.warning(f"-- __ __ -- {key} : {val}")

            # create_on_ui_requires_resources = config.get(
            #     'ckan.dataset.create_on_ui_requires_resources'
            # )
            # logging.warning(f"--- ___ --- ___ IM GONNA CREATE MY RESOURCE VIEW HERE")
            # resource_view = get_action("package_create_default_resource_views")({}, {
            #     "package" : pkg_dict,
            #     "create_datastore_views" : True,
            # })
            # if not resource_view:
            #     logging.warning(f"-- __ -- __ -- __ damn well failed creating a resource view innit bruv")
            # else:
            #     logging.warning(f"__ -- __ -- __ -- RESOURCE VIEW SUCCESSFULLY CREATED. PRINTING RESOURCE VIEW")
            #     for each_view in resource_view:
            #         for key, val in resource_view.items():
            #             logging.warning(f" --- ___ ___ --- {key} : {val}")

            new_or_existing = pkg_dict["new_or_existing"]
            if ckan_phase:
                if new_or_existing == "Add New Dataset":
                    # redirect to add dataset resources if
                    # create_on_ui_requires_resources is set to true
                    logging.warning(
                        f"THIS IS ADDING A NEW DATASET!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                    )
                    url = h.url_for(
                        "{}_resource.new".format(package_type), id=pkg_dict["name"]
                    )
                    return h.redirect_to(url)
                logging.warning(
                    f"THIS IS REFERENCING FROM CLEARMLLLLLLLLLLLLLLLLLLLLLLLLLL"
                )

                get_action("package_update")(
                    cast(Context, dict(context, allow_state_change=True)),
                    dict(pkg_dict, state="active"),
                )
                logging.warning(f"TRYING TO REDIRECT NOW!!!!!!!!!!!!!!!!!!!")
                return h.redirect_to("{}.read".format(package_type), id=pkg_dict["id"])

            return _form_save_redirect(
                pkg_dict["name"], "new", package_type=package_type
            )

        except NotAuthorized:
            return base.abort(403, _("Unauthorized to read package"))
        except NotFound:
            return base.abort(404, _("Dataset not found"))
        except SearchIndexError as e:
            try:
                exc_str = str(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = str(str(e))
            return base.abort(
                500, _("Unable to add package to search index.") + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action("package_show")(context, data_dict)
                data_dict["state"] = pkg_dict["state"]
                return EditPackageView().get(
                    package_type, data_dict["id"], data_dict, errors, error_summary
                )
            data_dict["state"] = "none"
            return self.get(package_type, data_dict, errors, error_summary)

    def get(
        self,
        package_type: str,
        data: Optional[dict[str, Any]] = None,
        errors: Optional[dict[str, Any]] = None,
        error_summary: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        This function is called when its URL endpoint is called. 
        For this function, it is called when the URL endpoint '/dataset/new' is called.

        Check /views/dataset.py for the documentation.
        """
        context = self._prepare()
        if data and "type" in data:
            package_type = data["type"]

        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(parse_params(request.args, ignore_keys=CACHE_PARAMETERS))
            )
        )
        resources_json = h.json.dumps(data.get("resources", []))
        # convert tags if not supplied in data
        if data and not data.get("tag_string"):
            data["tag_string"] = ", ".join(
                h.dict_list_reduce(data.get("tags", {}), "name")
            )

        errors = errors or {}
        error_summary = error_summary or {}
        # in the phased add dataset we need to know that
        # we have already completed stage 1
        stage = ["active"]
        if data.get("state", "").startswith("draft"):
            stage = ["active", "complete"]

        # if we are creating from a group then this allows the group to be
        # set automatically
        data["group_id"] = request.args.get("group") or request.args.get(
            "groups__0__id"
        )

        # Adding group list!!
        groupList = get_action("group_list")({}, {})
        logging.warning(f"*^*^*^*^ ***** __________ group list: {groupList}")

        form_snippet = _get_pkg_template("package_form", package_type=package_type)
        form_vars: dict[str, Any] = {
            "data": data,
            "errors": errors,
            "error_summary": error_summary,
            "action": "new",
            "stage": stage,
            "dataset_type": package_type,
            "form_style": "new",
            "groupList" : groupList,
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(context, {}, package_type=package_type)

        new_template = _get_pkg_template("new_template", package_type)
        return base.render(
            new_template,
            extra_vars={
                "form_vars": form_vars,
                "form_snippet": form_snippet,
                "dataset_type": package_type,
                "resources_json": resources_json,
                "form_snippet": form_snippet,
                "errors_json": errors_json,
                "groupList" : groupList,
            },
        )


def edit_groups(pkg_dict):
    """
    This function is used to add more groups for a dataset.

    Args:
        pkg_dict (dict): pkg_dict is a dictionary of the form that the user submitted

    Returns:
        pkg_dict (dict): updated pkg_dict with new groups
    """
    if "subject_tags" in pkg_dict:
        logging.warning(f"________________*********************** {pkg_dict['subject_tags']}")
        if isinstance(pkg_dict['subject_tags'], str):
            pkg_dict['subject_tags'] = pkg_dict['subject_tags'].strip("[]")
            pkg_dict['subject_tags'] = pkg_dict['subject_tags'].replace("'", "")
            pkg_dict['subject_tags'] = pkg_dict['subject_tags'].split(', ')
            logging.warning(f"subject tag: {pkg_dict['subject_tags']}")
            # pkg_dict['subject_tags'] = list(pkg_dict['subject_tags'])
        # logging.warning(f"****************** SUBJECT TAGS:")
        # logging.warning(f"\t\t __** TAG: {pkg_dict['subject_tags']}")
        groups_list = []
        for groupname in pkg_dict['subject_tags']:
            groups_list.append({
                'name' : groupname
            })
        for group in groups_list:
            pkg_dict['groups'].append(group)
        del pkg_dict['subject_tags']

        # for key, val in pkg_dict.items():
        #     logging.warning(f"******* {key} : {val}")
        admin = toolkit.config.get("ckan_sysadmin_name")
        password = toolkit.config.get("ckan_sysadmin_password")

        logging.warning(f"*^_*^_*^_*^_ ADMIN: {admin}, PASSWORD: {password}")
        logging.warning(f"pkg_dict['groups'] : {pkg_dict['groups']}")
        pkg_dict = get_action("package_patch")({
            # "ignore_auth" : True,
            'user' : admin,
            'password' : password,
        }, pkg_dict)

        for key, val in pkg_dict.items():
            logging.warning(f"*******_____________ {key} : {val}")
    return pkg_dict


class EditPackageView(MethodView):
    def _is_save(self) -> bool:
        return "save" in request.form

    def _prepare(self) -> Context:  # noqa
        context = cast(
            Context,
            {
                "model": model,
                "session": model.Session,
                "user": current_user.name,
                "auth_user_obj": current_user,
                "save": self._is_save(),
            },
        )
        try:
            check_access("package_create", context)
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to create a package"))
        return context

    def post(self, package_type: str, id: str) -> Union[Response, str]:
        context = self._prepare()
        package_type = _get_package_type(id) or package_type
        log.debug("Package save request name: %s POST: %r", id, request.form)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
            files = dict_fns.unflatten(tuplize_dict(parse_params(request.files)))

            logging.warning(f"-- ---- ---- VIEWS.py ---------- EDITING PACKAGE ")
            logging.warning(f"-- ---- ---- FILES: {files} ----------------------------")
            data_dict.update(clean_dict(files))
        except dict_fns.DataError:
            return base.abort(400, _("Integrity Error"))
        try:
            if "_ckan_phase" in data_dict:
                # we allow partial updates to not destroy existing resources
                context["allow_partial_update"] = True
                if "tag_string" in data_dict:
                    data_dict["tags"] = _tag_string_to_list(data_dict["tag_string"])
                del data_dict["_ckan_phase"]
                del data_dict["save"]
            data_dict["id"] = id

            # i think this is a problem that its deleting the rest of the metadata, 
            # # so im gonna change this to package_patch
            # pkg_dict = get_action("package_update")(context, data_dict)
            # if this is passing in empty things, 
            # # i think can just retrieve original package then fill in i guess. 
            # # but means i cant delete content??
            for key, val in data_dict.items():
                logging.warning(f"^^^^^^ {key} : {val}")
            logging.warning(f"_*^_*^_*^_*^ Patching this package")
            temp = []
            subject_tags = None
            if "subject_tags" in data_dict:
                subject_tags = str(data_dict['subject_tags'])
                logging.warning(f"subject Tags:::::::::::::::: {subject_tags}")
                del data_dict['subject_tags']
            for key, val in data_dict.items():
                # logging.warning(f"_*^_*^ {key} : {val} + {type(val)}")
                if val == '':
                    temp.append(key)
            for key in temp:
                del data_dict[key]
            # for key, val in data_dict.items():
            #     logging.warning(f"_*^_*^ {key} : {val}")
            

            pkg_dict = get_action("package_patch")(context, data_dict)
            if subject_tags:
                pkg_dict['subject_tags'] = subject_tags
                pkg_dict = edit_groups(pkg_dict)

            
            if data_dict['upload']:
                resource = get_action(f"resource_create")(
                    {},
                    {
                        "package_id": pkg_dict["id"],
                        "upload": data_dict["upload"],
                        "preview": True,
                        "format": "",
                    },
                )

                pkg_dict["resources"].append(resource)
                pkg_dict = get_action("package_patch")({}, pkg_dict)
            logging.warning(f"____^^^*** LAST DATADICT IN EDIT:::::::::::")
            for key, val in pkg_dict.items():
                logging.warning(f"_*^_*^ {key} : {val}")


            return _form_save_redirect(
                pkg_dict["name"], "edit", package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to read package %s") % id)
        except NotFound:
            return base.abort(404, _("Dataset not found"))
        except SearchIndexError as e:
            try:
                exc_str = str(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = str(str(e))
            return base.abort(500, _("Unable to update search index.") + exc_str)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(package_type, id, data_dict, errors, error_summary)

    def get(
        self,
        package_type: str,
        id: str,
        data: Optional[dict[str, Any]] = None,
        errors: Optional[dict[str, Any]] = None,
        error_summary: Optional[dict[str, Any]] = None,
    ) -> Union[Response, str]:
        context = self._prepare()
        package_type = _get_package_type(id) or package_type
        try:
            view_context = context.copy()
            view_context["for_view"] = True
            pkg_dict = get_action("package_show")(view_context, {"id": id})
            context["for_edit"] = True
            old_data = get_action("package_show")(context, {"id": id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            if data:
                old_data.update(data)
            data = old_data
        except (NotFound, NotAuthorized):
            return base.abort(404, _("Dataset not found"))
        assert data is not None
        # are we doing a multiphase add?
        if data.get("state", "").startswith("draft"):
            g.form_action = h.url_for("{}.new".format(package_type))
            g.form_style = "new"

            return CreatePackageView().get(
                package_type, data=data, errors=errors, error_summary=error_summary
            )

        pkg = context.get("package")
        resources_json = h.json.dumps(data.get("resources", []))
        user = current_user.name
        try:
            check_access("package_update", context)
        except NotAuthorized:
            return base.abort(403, _("User %r not authorized to edit %s") % (user, id))
        # convert tags if not supplied in data
        if data and not data.get("tag_string"):
            data["tag_string"] = ", ".join(
                h.dict_list_reduce(pkg_dict.get("tags", {}), "name")
            )

        # Adding group list!!
        groupList = get_action("group_list")({}, {})
        logging.warning(f"*^*^*^*^ ***** __________ group list: {groupList}")

        errors = errors or {}
        form_snippet = _get_pkg_template("package_form", package_type=package_type)
        form_vars: dict[str, Any] = {
            "data": data,
            "errors": errors,
            "error_summary": error_summary,
            "action": "edit",
            "dataset_type": package_type,
            "form_style": "edit",
            "groupList" : groupList,
            "is_edit": True
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.pkg = pkg
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(context, {"id": id}, package_type=package_type)

        # we have already completed stage 1
        form_vars["stage"] = ["active"]
        if data.get("state", "").startswith("draft"):
            form_vars["stage"] = ["active", "complete"]

        edit_template = _get_pkg_template("edit_template", package_type)
        return base.render(
            edit_template,
            extra_vars={
                "form_vars": form_vars,
                "form_snippet": form_snippet,
                "dataset_type": package_type,
                "pkg_dict": pkg_dict,
                "pkg": pkg,
                "resources_json": resources_json,
                "form_snippet": form_snippet,
                "errors_json": errors_json,
            },
        )


def deleteClearML(package_id):
    """
    This function is used to delete the dataset on ClearML side.

    Args:
        package_id (str): package ID to be deleted.

    Returns:
        status, errorMsg:
            Status = True / False, depending on success of deleting in ClearML.
            errorMsg = Error message if it fails.

    """
    package = get_action("package_show")(
        {},
        {
            "id": package_id,
        },
    )
    logging.warning(f"_*^_*^ DELETING CLEARML DATASET FIRST!!")
    try:
        logging.warning(f"_*^_*^_*^ ID: {package['clearml_id']}")
        logging.warning(f"_*^_*^_*^ PROJECT TITLE: {package['project_title']}")
        logging.warning(f"_*^_*^_*^ DATASET TITLE: {package['dataset_title']}")
        logging.warning(f"_*^_*^_*^ VERSION: {package['version']}")
        Dataset.delete(
            dataset_id=package["clearml_id"],
        )
        logging.warning(f"_*^_*^ Successfully deleted Dataset in ClearML")
        return True, None
    except Exception as e:
        logging.warning(f"_*^_*^_*^ Theres some issues babe: {e}")
        return False, e
    

class DeletePackageView(MethodView):
    def _prepare(self) -> Context:
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'auth_user_obj': current_user
        })
        return context

    def post(self, package_type: str, id: str) -> Response:
        if u'cancel' in request.form:
            return h.redirect_to(u'{}.edit'.format(package_type), id=id)
        context = self._prepare()
        try:
            # get_action(u'package_delete')(context, {u'id': id})
            clearml_delete_status, errorMsg = deleteClearML(id)
            
            if clearml_delete_status == True:
                admin = toolkit.config.get("ckan_sysadmin_name")
                password = toolkit.config.get("ckan_sysadmin_password")
                # Using sys_admin to override here
                logging.warning(f"_*^_*^ PURGING DATASET NOW. GIMME A MOMENT BABE")
                get_action("dataset_purge")({
                    'user' : admin,
                    'password' : password,
                }, 
                {
                    "id": id,
                })
            else:
                return base.abort(
                    403, _(f"Unable to delete on ClearML side. Error: {errorMsg}")
                )
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete package %s') % u''
            )

        h.flash_notice(_(u'Dataset has been deleted.'))
        return h.redirect_to(package_type + u'.search')

    def get(self, package_type: str, id: str) -> Union[Response, str]:
        context = self._prepare()
        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete package %s') % u''
            )

        dataset_type = pkg_dict[u'type'] or package_type

        # TODO: remove
        g.pkg_dict = pkg_dict

        return base.render(
            u'package/confirm_delete.html', {
                u'pkg_dict': pkg_dict,
                u'dataset_type': dataset_type
            }
        )


def change_dataset_title(pkg_dict):
    """
    This function is used to change the dataset title. 
    Similar to the code written in `after_dataset_create()` in packagecontroller extension's `plugin.py`.

    Args:
        pkg_dict (dict): The whole package dictionary

    Returns:
        pkg_dict (dict): The whole package dictionary with the new titles.
    """
    dataset = None
    try:
        dataset = Dataset.get(dataset_id=pkg_dict["clearml_id"])
        # put the download url in pkg_dict'
    except Exception as e:
        logging.warning(
            f"ClearML ID:{pkg_dict['clearml_id']} does not exist in the ClearML database."
        )

    if dataset == None:
        logging.warning(
            f"****************CLEARML ID IS NOT VALID. DID NOT MANAGE TO RETRIEVE DATASET"
        )
        return pkg_dict

    pkg_dict["clearml_download_url"] = dataset.get_default_storage()

    # Changing metadata fields for the things below
    pkg_dict["project_title"] = dataset.project
    pkg_dict["dataset_title"] = dataset.name + " v" + dataset._dataset_version
    pkg_dict["title"] = dataset.name + " v" + dataset._dataset_version
    # new_title = dataset.name + " v" + dataset._dataset_version
    pkg_dict['version'] = dataset._dataset_version
    # new_title = dataset.name + "-v" + dataset._dataset_version
    # new_title = new_title.replace(" ", "-")
    # new_title = new_title.replace(".", "-")
    # new_title = new_title.lower()
    # logging.warning(f"---------- NEW NAME: {new_title}")
    # pkg_dict['name'] = new_title
    # pkg_dict["title"] = new_title

    new_pkg_dict = get_action("package_update")({}, pkg_dict)
    logging.warning(f"-----*****----- THIS IS THE UPDATED PKG DICT -----*****-----")
    for key, val in new_pkg_dict.items():
        logging.warning(f"***** {key} : {val} -----")

    return new_pkg_dict


def upload_to_clearml(
    path_to_folder,
    path_to_file,
    package_id,
    project_title,
    dataset_title,
    parent_datasets,
):
    """
    This function handles the uploading to ClearML.
    We retrieve the uploaded files through path_to_folder / path_to_file and upload them to ClearML as a dataset.
    We also check for possible parent_datasets that users might want their dataset to inherit from.

    Args:
        path_to_folder (str): folder path for uploaded folders
        path_to_file (str): file path for uploaded file
        package_id (str): package ID (Not used)
        project_title (str): Project title to be named in ClearML
        dataset_title (str): Dataset title to be named in ClearML
        parent_datasets (str): Parent Datasets that new dataset should inherit from.

    Returns:
        dataset.id (str): returns the ID of the newly created dataset in ClearML so that we can store this ID in DataVerse.
    """
    logging.warning(f"Package ID: {package_id}")
    logging.warning(f"Folder Path: {path_to_folder}")
    logging.warning(f"Project Title: {project_title}")
    logging.warning(f"Dataset Title: {dataset_title}")
    logging.warning(f"Parent Datasets: {parent_datasets}")
    if parent_datasets:
        dataset = Dataset.create(
            dataset_project=project_title,
            dataset_name=dataset_title,
            parent_datasets=list(parent_datasets),
        )
    else:
        dataset = Dataset.get(
            dataset_project=project_title, dataset_name=dataset_title, auto_create=True
        )

    logging.warning(f"----------ADDING FILES TO DATASET----------")
    if path_to_folder != None:
        dataset.add_files(path=r"{}".format(path_to_folder))
    if path_to_file != None:
        dataset.add_files(path=r"{}".format(path_to_file))
    logging.warning(f"----------UPLOADING TO CLEARML----------")
    dataset.upload(show_progress=True, verbose=True)
    logging.warning(f"----------FINALIZING DATASET----------")
    # if resource_show['save'] =='go-metadata':
    dataset.finalize(verbose=True, raise_on_error=True, auto_upload=True)
    return dataset.id

# resource.py
# For Resource Form
class CreateResourceView(MethodView):
    """
    This is not used for now as for some reason the blueprint is not registering this class but the original one.
    Please refer to /views/resource.py for the changes that we added.
    """

    def post(self, package_type: str, id: str) -> Union[str, Response]:
        logging.warning(
            "__________________________________________________________________________"
        )
        logging.warning("THIS IS THE FIRST LINE OF POST IN RESOURCE for VIEWS.PY")
        package_details = get_action("package_show")({}, {"id": id})
        logging.warning(f"Package Details: ")
        for key, val in package_details.items():
            logging.warning(f"{key} : {val}")
        parent_ids = []
        if "extras" in package_details:
            for extra in package_details["extras"]:
                parent_ids.append(extra["key"])
        try:
            for parent_id in parent_ids:
                ds = Dataset.get(dataset_id=parent_id)
        except Exception as e:
            return base.abort(404, _("Invalid Parent ID"))
        save_action = request.form.get("save")
        data = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
        logging.warning(
            f"_________ PRINTING DATA DICTIONARY IN RESOURCE.PY ___________"
        )
        for key, val in data.items():
            logging.warning(f"------------------ {key} : {val}")
        files = dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
        logging.warning(f"THIS IS THE CONTENT OF THE FILES: {files}")
        defaultpath = r"/var/lib/ckan/default"
        folderpath = None
        pathtofolder = None
        pathtofile = None
        if isinstance(files["upload"], list):
            logging.warning(f"---- ---- -- ---- ---- IM ONLY JUST A FOLDER")
            for eachfile in files["upload"]:
                splitFileName = eachfile.filename.split("/")
                # (comment) splitFileName == [""] when the file upload or folder upload is not filled
                if splitFileName == [""]:
                    continue
                if len(splitFileName) > 1:
                    folderpath = defaultpath
                    filepath = defaultpath
                    pathtofolder = os.path.join(defaultpath, splitFileName[0])
                    for i in range(len(splitFileName)):
                        filepath = os.path.join(filepath, splitFileName[i])
                        if i != len(splitFileName) - 1:
                            folderpath = os.path.join(folderpath, splitFileName[i])
                    os.makedirs(folderpath, exist_ok=True)
                    eachfile.save(filepath)
                else:
                    pathtofile = defaultpath + "/temp/"
                    os.makedirs(pathtofile, exist_ok=True)
                    logging.warning(f"split file name: {splitFileName}")
                    filepath = os.path.join(pathtofile, splitFileName[0])
                    logging.warning(f"FILE PATH: {filepath}")
                    if os.path.isdir(filepath):
                        logging.error(f"{filepath} is a directory")
                    else:
                        eachfile.save(filepath)
        logging.warning(f"____-----_____----- printing path to folder: {pathtofolder}")
        logging.warning(f"____-----_____----- printing path to file: {pathtofile}")
        clearml_id = upload_to_clearml(
            pathtofolder,
            pathtofile,
            id,
            package_details["project_title"],
            package_details["dataset_title"],
            parent_ids,
        )

        package_details["clearml_id"] = clearml_id

        package_details = change_dataset_title(package_details)

        get_action("package_update")({}, package_details)
        # we don't want to include save as it is part of the form
        del data["save"]
        try:
            logging.warning(
                f"-- __ -- __ REMOVING UPLOADED FILES FROM CKAN AS IT IS UPLOADED TO CLEARML ALREADY."
            )
            shutil.rmtree(defaultpath)
        except Exception as e:
            logging.warning(
                f"-- __ -- __ UNABLE TO DELETE FOLDER FOR SOME GODFORSAKEN REASON: {e}"
            )
        context = cast(
            Context,
            {
                "model": model,
                "session": model.Session,
                "user": current_user.name,
                "auth_user_obj": current_user,
            },
        )

        # see if we have any data that we are trying to save
        data_provided = False
        for key, value in data.items():
            if (
                value or isinstance(value, cgi.FieldStorage)
            ) and key != "resource_type":
                data_provided = True
                break

        if not data_provided and save_action != "go-dataset-complete":
            if save_action == "go-dataset":
                # go to final stage of adddataset
                return h.redirect_to("{}.edit".format(package_type), id=id)
            # see if we have added any resources
            try:
                data_dict = get_action("package_show")(context, {"id": id})
            except NotAuthorized:
                return base.abort(403, _("Unauthorized to update dataset"))
            except NotFound:
                return base.abort(
                    404, _("The dataset {id} could not be found.").format(id=id)
                )
            if not len(data_dict["resources"]):
                # no data so keep on page
                msg = _("You must add at least one data resource")
                # On new templates do not use flash message

                errors: dict[str, Any] = {}
                error_summary = {_("Error"): msg}
                return self.get(package_type, id, data, errors, error_summary)

            # race condition if another user edits/deletes
            data_dict = get_action("package_show")(context, {"id": id})
            get_action("package_update")(
                cast(Context, dict(context, allow_state_change=True)),
                dict(data_dict, state="active"),
            )
            return h.redirect_to("{}.read".format(package_type), id=id)

        data["package_id"] = id
        if save_action == "go-metadata":
            # race condition if another user edits/deletes
            data_dict = get_action("package_show")(context, {"id": id})
            get_action("package_update")(
                cast(Context, dict(context, allow_state_change=True)),
                dict(data_dict, state="active"),
            )
            return h.redirect_to("{}.read".format(package_type), id=id)
        elif save_action == "go-dataset":
            # go to first stage of add dataset
            return h.redirect_to("{}.edit".format(package_type), id=id)
        elif save_action == "go-dataset-complete":
            return h.redirect_to("{}.read".format(package_type), id=id)
        else:
            # add more resources
            return h.redirect_to("{}_resource.new".format(package_type), id=id)

    def get(
        self,
        package_type: str,
        id: str,
        data: Optional[dict[str, Any]] = None,
        errors: Optional[dict[str, Any]] = None,
        error_summary: Optional[dict[str, Any]] = None,
    ) -> str:
        # get resources for sidebar
        context = cast(
            Context,
            {
                "model": model,
                "session": model.Session,
                "user": current_user.name,
                "auth_user_obj": current_user,
            },
        )
        try:
            pkg_dict = get_action("package_show")(context, {"id": id})
        except NotFound:
            return base.abort(
                404, _("The dataset {id} could not be found.").format(id=id)
            )
        try:
            check_access("resource_create", context, {"package_id": pkg_dict["id"]})
        except NotAuthorized:
            return base.abort(
                403, _("Unauthorized to create a resource for this package")
            )

        package_type = pkg_dict["type"] or package_type

        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars: dict[str, Any] = {
            "data": data,
            "errors": errors,
            "error_summary": error_summary,
            "action": "new",
            "resource_form_snippet": _get_pkg_template("resource_form", package_type),
            "dataset_type": package_type,
            "pkg_name": id,
            "pkg_dict": pkg_dict,
        }
        template = "package/new_resource_not_draft.html"
        if pkg_dict["state"].startswith("draft"):
            extra_vars["stage"] = ["complete", "active"]
            template = "package/new_resource.html"
        return base.render(template, extra_vars)