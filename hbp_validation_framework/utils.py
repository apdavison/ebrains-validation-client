"""
Miscellaneous methods that help in different aspects of model validation.
Does not require explicit instantiation.

The following methods are available:

=======================================   ====================================
Action                                    Method
=======================================   ====================================
View JSON data in web browser             :meth:`view_json_tree`
Prepare test for execution                :meth:`prepare_run_test_offline`
Run the validation test                   :meth:`run_test_offline`
Register result with validation service   :meth:`upload_test_result`
Run test and register result              :meth:`run_test`
Download PDF report of test results       :meth:`generate_report`
Obtain score matrix for test results      :meth:`generate_score_matrix`
=======================================   ====================================
"""

import os
import json
import pickle
import webbrowser
import argparse
import collections
import unicodedata
try:
    raw_input
except NameError:  # Python 3
    raw_input = input
import sciunit
from datetime import datetime
from . import TestLibrary, ModelCatalog
from .datastores import CollabDataStore, URI_SCHEME_MAP
try:  # Python 3
    from urllib.parse import urlparse
except ImportError:  # Python 2
    from urlparse import urlparse
from importlib import import_module
import mimetypes
import math
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path  # Python 2 backport

def view_json_tree(data):
    """Displays the JSON tree structure inside the web browser

    This method can be used to view any JSON data, generated by any of the
    validation client's methods, in a tree-like representation.

    Parameters
    ----------
    data : string
        JSON object represented as a string.

    Returns
    -------
    None
        Does not return any data. JSON displayed inside web browser.

    Examples
    --------
    >>> model = model_catalog.get_model(alias="HCkt")
    >>> from hbp_validation_framework import utils
    >>> utils.view_json_tree(model)
    """

    _make_js_file(data)

    script_dir = os.path.dirname(__file__)
    rel_path = "jsonTreeViewer/index.htm"
    abs_file_path = os.path.join(script_dir, rel_path)
    webbrowser.open(abs_file_path, new=2)

def _make_js_file(data):
    """
    Creates a JavaScript file from give JSON object; loaded by the browser
    This eliminates cross-origin issues with loading local data files (e.g. via jQuery)
    """

    script_dir = os.path.dirname(__file__)
    rel_path = "jsonTreeViewer/data.js"
    abs_file_path = os.path.join(script_dir, rel_path)
    with open(abs_file_path, 'w') as outfile:
        outfile.write("var data = '")
        json.dump(data, outfile)
        outfile.write("'")

def prepare_run_test_offline(username="", password=None, environment="production", test_instance_id="", test_id="", test_alias="", test_version="", client_obj=None, **params):
    """Gather info necessary for running validation test

    This method will select the specified test and prepare a config file
    enabling offline execution of the validation test. The observation file
    required by the test is also downloaded and stored locally.
    The test can be specified in the following ways (in order of priority):

    1. specify `test_instance_id` corresponding to test instance in test library
    2. specify `test_id` and `test_version`
    3. specify `test_alias` and `test_version`
    Note: for (2) and (3) above, if `test_version` is not specified,
          then the latest test version is retrieved

    Parameters
    ----------
    username : string
        Your HBP Collaboratory username.
    password : string
        Your HBP Collaboratory password.
    environment : string, optional
        Used to indicate whether being used for development/testing purposes.
        Set as `production` as default for using the production system,
        which is appropriate for most users. When set to `dev`, it uses the
        `development` system. For other values, an external config file would
        be read (the latter is currently not implemented).
    test_instance_id : UUID
        System generated unique identifier associated with test instance.
    test_id : UUID
        System generated unique identifier associated with test definition.
    test_alias : string
        User-assigned unique identifier associated with test definition.
    test_version : string
        User-assigned identifier (unique for each test) associated with test instance.
    client_obj : ModelCatalog/TestLibrary object
        Used to easily create a new ModelCatalog/TestLibrary object if either exist already.
        Avoids need for repeated authentications; improves performance. Also, helps minimize
        being blocked out by the authentication server for repeated authentication requests
        (applicable when running several tests in quick succession, e.g. in a loop).
    **params : list
        Keyword arguments to be passed to the Test constructor.

    Note
    ----
    Should be run on node having access to external URLs (i.e. with internet access)

    Returns
    -------
    path
        The absolute path of the generated test config file

    Examples
    --------
    >>> test_config_file = utils.prepare_run_test_offline(username="shailesh", test_alias="CDT-5", test_version="5.0")
    """

    if client_obj:
        test_library = TestLibrary.from_existing(client_obj)
    else:
        test_library = TestLibrary(username, password, environment=environment)

    if test_instance_id == "" and test_id == "" and test_alias == "":
        raise Exception("test_instance_id or test_id or test_alias needs to be provided for finding test.")

    # Gather specified test info
    test_instance_json = test_library.get_test_instance(instance_id=test_instance_id, test_id=test_id, alias=test_alias, version=test_version)
    test_id = test_instance_json["test_definition_id"]
    test_instance_id = test_instance_json["id"]
    test_instance_path = test_instance_json["path"]

    # Download test observation to local storage
    test_observation_path = test_library.get_test_definition(test_id=test_id)["data_location"]
    parse_result = urlparse(test_observation_path)
    datastore = URI_SCHEME_MAP[parse_result.scheme](auth=test_library.auth)
    base_folder = os.path.join(os.getcwd(), "hbp_validation_framework", test_id, datetime.now().strftime("%Y%m%d-%H%M%S"))
    test_observation_file = datastore.download_data([test_observation_path], local_directory=base_folder)[0]

    # Create test config required for offline execution
    test_info = {}
    test_info["test_id"] = test_id
    test_info["test_instance_id"] = test_instance_id
    test_info["test_instance_path"] = test_instance_path
    test_info["test_observation_file"] = os.path.basename(os.path.realpath(test_observation_file))
    test_info["params"] = params

    # Save test info to config file
    test_config_file = os.path.join(base_folder, "test_config.json")
    with open(test_config_file, 'w') as file:
        file.write(json.dumps(test_info, indent=4))
    return test_config_file

def run_test_offline(model="", test_config_file=""):
    """Run the validation test

    This method will accept a model, located locally, run the test specified
    via the test config file (generated by :meth:`prepare_run_test_offline`),
    and store the results locally.

    Parameters
    ----------
    model : sciunit.Model
        A :class:`sciunit.Model` instance.
    test_config_file : string
        Absolute path of the test config file generated by :meth:`prepare_run_test_offline`

    Note
    ----
    Can be run on node(s) having no access to external URLs (i.e. without internet access).
    Also, it is required that the test_config_file and the test_observation_file are located
    in the same directory.

    Returns
    -------
    path
        The absolute path of the generated test result file

    Examples
    --------
    >>> test_result_file = utils.run_test_offline(model=model, test_config_file=test_config_file)
    """

    if not os.path.isfile(test_config_file) :
        raise Exception("'test_config_file' should direct to file describing the test configuration.")
    base_folder = os.path.dirname(os.path.realpath(test_config_file))

    # Load the test info from config file
    with open(test_config_file) as file:
        test_info = json.load(file)

    # Identify test class path
    path_parts = test_info["test_instance_path"].split(".")
    cls_name = path_parts[-1]
    module_name = ".".join(path_parts[:-1])
    test_module = import_module(module_name)
    test_cls = getattr(test_module, cls_name)

    # Read observation data required by test
    with open(os.path.join(base_folder, test_info["test_observation_file"]), 'r') as file:
        observation_data = file.read()
    content_type = mimetypes.guess_type(test_info["test_observation_file"])[0]
    if content_type == "application/json":
        observation_data = json.loads(observation_data)

    # Create the :class:`sciunit.Test` instance
    params = test_info["params"]
    test = test_cls(observation=observation_data, **params)
    test.uuid = test_info["test_instance_id"]

    print("----------------------------------------------")
    print("Test name: ", test.name)
    print("Test type: ", type(test))
    print("----------------------------------------------")

    # Check the model
    if not isinstance(model, sciunit.Model):
        raise TypeError("`model` is not a sciunit Model!")
    print("----------------------------------------------")
    print("Model name: ", model.name)
    print("Model type: ", type(model))
    print("----------------------------------------------")

    # Run the test
    t_start = datetime.utcnow()
    score = test.judge(model, deep_error=True)
    t_end = datetime.utcnow()

    print("----------------------------------------------")
    print("Score: ", score.score)
    if "figures" in score.related_data:
        print("Output files: ")
        for item in score.related_data["figures"]:
            print(item)
    print("----------------------------------------------")

    score.runtime = str(int(math.ceil((t_end-t_start).total_seconds()))) + " s"
    score.exec_timestamp = t_end
    # score.exec_platform = str(self._get_platform())

    # Save result info to file
    Path(os.path.join(base_folder, "results")).mkdir(parents=True, exist_ok=True)
    test_result_file = os.path.join(base_folder, "results", "result__" + model.name + "__" + datetime.now().strftime("%Y%m%d%H%M%S") + ".pkl")
    with open(test_result_file, 'wb') as file:
        pickle.dump(score, file)
    return test_result_file

def upload_test_result(username="", password=None, environment="production", test_result_file="", storage_collab_id="", register_result=True, client_obj=None):
    """Register the result with the Validation Service

    This method will register the validation result specified via the test result file
    (generated by :meth:`run_test_offline`) with the validation service.

    Parameters
    ----------
    username : string
        Your HBP Collaboratory username.
    password : string
        Your HBP Collaboratory password.
    environment : string, optional
        Used to indicate whether being used for development/testing purposes.
        Set as `production` as default for using the production system,
        which is appropriate for most users. When set to `dev`, it uses the
        `development` system. For other values, an external config file would
        be read (the latter is currently not implemented).
    test_result_file : string
        Absolute path of the test result file generated by :meth:`run_test_offline`
    storage_collab_id : string
        Collab ID where output files should be stored; if empty, stored in model's host Collab.
    register_result : boolean
        Specify whether the test results are to be scored on the validation framework.
        Default is set as True.
    client_obj : ModelCatalog/TestLibrary object
        Used to easily create a new ModelCatalog/TestLibrary object if either exist already.
        Avoids need for repeated authentications; improves performance. Also, helps minimize
        being blocked out by the authentication server for repeated authentication requests
        (applicable when running several tests in quick succession, e.g. in a loop).

    Note
    ----
    Should be run on node having access to external URLs (i.e. with internet access)

    Returns
    -------
    UUID
        UUID of the test result that has been created.
    object
        score object evaluated by the test.

    Examples
    --------
    >>> result_id, score = utils.upload_test_result(username="shailesh", test_result_file=test_result_file)
    """

    if not register_result:
        return None, None
    if not os.path.isfile(test_result_file) :
        raise Exception("'test_result_file' should direct to file containg the test result data.")

    # Load result info from file
    with open(test_result_file, 'rb') as file:
        score = pickle.load(file)

    # Register the result with the HBP validation framework
    if client_obj:
        model_catalog = ModelCatalog.from_existing(client_obj)
    else:
        model_catalog = ModelCatalog(username, password, environment=environment)
    model_instance_uuid = model_catalog.find_model_instance_else_add(score.model)
    model_instance_json = model_catalog.get_model_instance(instance_id=model_instance_uuid)
    model_json = model_catalog.get_model(model_id=model_instance_json["model_id"])
    model_host_collab_id = model_json["app"]["collab_id"]
    model_name = model_json["name"]

    if not storage_collab_id:
        storage_collab_id = model_host_collab_id
    score.related_data["project"] = storage_collab_id

    # Check if result with same hash has already been uploaded for
    # this (model instance, test instance) combination; if yes, don't register result
    result_json = {
                    "model_instance_id": model_instance_uuid,
                    "test_code_id": score.test.uuid,
                    "score": score.score,
                    "runtime": score.runtime,
                    "exectime": score.exec_timestamp#,
                    # "platform": score.exec_platform
                  }
    score.score_hash = str(hash(json.dumps(result_json, sort_keys=True, default = str)))
    test_library = TestLibrary.from_existing(model_catalog)
    results = test_library.list_results(model_version_id=model_instance_uuid, test_code_id=score.test.uuid)["results"]
    duplicate_results =  [x["id"] for x in results if x["hash"] == score.score_hash]
    if duplicate_results:
        raise Exception("An identical result has already been registered on the validation framework.\nExisting Result UUID = {}".format(", ".join(duplicate_results)))

    collab_folder = "validation_results/{}/{}_{}".format(datetime.now().strftime("%Y-%m-%d"),model_name, datetime.now().strftime("%Y%m%d-%H%M%S"))
    collab_storage = CollabDataStore(collab_id=storage_collab_id,
                                     base_folder=collab_folder,
                                     auth=test_library.auth)

    response = test_library.register_result(test_result=score, data_store=collab_storage)
    return response, score

def run_test(username="", password=None, environment="production", model="", test_instance_id="", test_id="", test_alias="", test_version="", storage_collab_id="", register_result=True, client_obj=None, **params):
    """Run validation test and register result

    This will execute the following methods by relaying the output of one to the next:
    1. :meth:`prepare_run_test_offline`
    2. :meth:`run_test_offline`
    3. :meth:`upload_test_result`

    Parameters
    ----------
    username : string
        Your HBP Collaboratory username.
    password : string
        Your HBP Collaboratory password.
    environment : string, optional
        Used to indicate whether being used for development/testing purposes.
        Set as `production` as default for using the production system,
        which is appropriate for most users. When set to `dev`, it uses the
        `development` system. For other values, an external config file would
        be read (the latter is currently not implemented).
    model : sciunit.Model
        A :class:`sciunit.Model` instance.
    test_instance_id : UUID
        System generated unique identifier associated with test instance.
    test_id : UUID
        System generated unique identifier associated with test definition.
    test_alias : string
        User-assigned unique identifier associated with test definition.
    test_version : string
        User-assigned identifier (unique for each test) associated with test instance.
    storage_collab_id : string
        Collab ID where output files should be stored; if empty, stored in model's host Collab.
    register_result : boolean
        Specify whether the test results are to be scored on the validation framework.
        Default is set as True.
    client_obj : ModelCatalog/TestLibrary object
        Used to easily create a new ModelCatalog/TestLibrary object if either exist already.
        Avoids need for repeated authentications; improves performance. Also, helps minimize
        being blocked out by the authentication server for repeated authentication requests
        (applicable when running several tests in quick succession, e.g. in a loop).
    **params : list
        Keyword arguments to be passed to the Test constructor.

    Note
    ----
    Should be run on node having access to external URLs (i.e. with internet access)

    Returns
    -------
    UUID
        UUID of the test result that has been created.
    object
        score object evaluated by the test.

    Examples
    --------
    >>> result_id, score = utils.run_test(username="HBP_USERNAME", password="HBP_PASSWORD" environment="production", model=cell_model, test_alias="basalg_msn_d1", test_version="1.0", storage_collab_id="8123", register_result=True)
    """

    test_config_file = prepare_run_test_offline(username=username, password=password, environment=environment, test_instance_id=test_instance_id, test_id=test_id, test_alias=test_alias, test_version=test_version, client_obj=client_obj, **params)
    test_result_file = run_test_offline(model=model, test_config_file=test_config_file)
    result_id, score = upload_test_result(username=username, password=password, environment=environment, test_result_file=test_result_file, storage_collab_id=storage_collab_id, register_result=register_result, client_obj=client_obj)
    return result_id, score

def generate_report(username="", password=None, environment="production", result_list=[], only_combined=True, client_obj=None):
    """Generates and downloads a PDF report of test results

    This method will generate and download a PDF report of the specified
    test results. The report will consist of all information relevant to
    that particular result, such as:

    * result info
    * model info
    * model instance info
    * test info
    * test instance info
    * output files associated with result

    Parameters
    ----------
    username : string
        Your HBP collaboratory username.
    environment : string, optional
        Used to indicate whether being used for development/testing purposes.
        Set as `production` as default for using the production system,
        which is appropriate for most users. When set to `dev`, it uses the
        `development` system. For other values, an external config file would
        be read (the latter is currently not implemented).
    result_list : list
        List of result UUIDs that need to be included in report.
    only_combined : boolean, optional
        Indicates whether only a single combined PDF should be saved. Set to
        `True` as default. When set to `False`, then `n+2` PDFs will be saved,
        where `n` is the number of valid result UUIDs. These would include:

        * Combined PDF report
        * Summary of call to `generate_report()`
        * One PDF for each valid result UUID

    client_obj : ModelCatalog/TestLibrary object
        Used to easily create a new ModelCatalog/TestLibrary object if either exist already.
        Avoids need for repeated authentications; improves performance. Also, helps minimize
        being blocked out by the authentication server for repeated authentication requests
        (applicable when running several tests in quick succession, e.g. in a loop).

    Returns
    -------
    list
        List of valid UUIDs for which the PDF report was generated
    path
        The absolute path of the generated report

    Examples
    --------
    >>> result_list = ["a618a6b1-e92e-4ac6-955a-7b8c6859285a", "793e5852-761b-4801-84cb-53af6f6c1acf"]
    >>> valid_uuids, report_path = utils.generate_report(username="shailesh", result_list=result_list)
    """
    # This method can be significantly improved in future.

    try:
        from fpdf import FPDF
    except ImportError:
        print("Please install the following package: fpdf")
        return
    try:
        from PyPDF2 import PdfFileMerger, PdfFileReader
    except ImportError:
        print("Please install the following package: PyPDF2")
        return

    class PDF(FPDF):
        def header(self):
            # Logo
            self.image('https://i.imgur.com/sHi1OSs.png', 80, 8, 50)
            # Arial bold 15
            self.set_font('Arial', 'B', 18)
            # Move to the right
            self.ln(15)
            self.cell(45)
            # Title
            self.cell(100, 10, 'Validation Framework Report', 1, 0, 'C')
            # Line break
            self.ln(20)

        # # Page footer
        # def footer(self):
        #     # Position at 1.5 cm from bottom
        #     self.set_y(-15)
        #     # Arial italic 8
        #     self.set_font('Arial', 'I', 8)
        #     # Page number
        #     self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

    if client_obj:
        model_catalog = ModelCatalog.from_existing(client_obj)
    else:
        model_catalog = ModelCatalog(username, password, environment=environment)
    test_library = TestLibrary.from_existing(model_catalog)
    result_data = {}
    valid_uuids = []

    for result_id in result_list:
        result = test_library.get_result(result_id=result_id)
        if len(result["results"]) != 0:
            valid_uuids.append(result_id)
            result_data[result_id] = result["results"][0]

    def _print_param_value(pdf, param, value, fontsize):
        pdf.set_font('Arial', 'B', fontsize)
        pdf.cell(40, 10, param)
        pdf.set_font('Arial', '', fontsize)
        pdf.cell(0, 10, value)

    pdf = PDF()
    # pdf.alias_nb_pages()

    timestamp = datetime.now()
    filename = str("HBP_VF_Report_" + timestamp.strftime("%Y%m%d-%H%M%S") + ".pdf")

    # Cover Page
    pdf.add_page()
    _print_param_value(pdf, "Report Name: ", filename, 14)
    pdf.ln(10)
    _print_param_value(pdf, "Created Date: ", timestamp.strftime("%Y-%m-%d %H:%M:%S"), 14)
    pdf.ln(20)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(40, 10, "Contains data for following Result UUIDs: ")
    pdf.ln(10)
    pdf.set_font('Arial', '', 14)

    for result_id in valid_uuids:
            pdf.cell(40)
            pdf.cell(0, 10, result_id)
            pdf.ln(10)

    if len(valid_uuids) < len(result_list):
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(40, 10, "Following UUIDs were invalid: ")
        pdf.ln(10)
        pdf.set_font('Arial', '', 14)
        for result_id in result_list:
            if result_id not in valid_uuids:
                pdf.cell(40)
                pdf.cell(0, 10, result_id)
                pdf.ln(10)

    pdf.ln(50)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, 'Report generated by the HBP Validation Framework', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 12)
    pdf.cell(90, 10, 'For more information, you may visit:')
    pdf.ln(10)
    pdf.cell(15)
    _print_param_value(pdf, "Python Client: ", "https://github.com/apdavison/hbp-validation-client/", 12)
    pdf.ln(10)
    pdf.cell(15)
    _print_param_value(pdf, "Documentation: ", "http://hbp-validation-client.readthedocs.io/", 12)

    if not os.path.exists("./report/"):
        os.makedirs("./report/")
    pdf.output(str("./report/"+filename[:-4]+"_cover.pdf"), 'F')
    result_ctr = 0

    # Result Pages
    for result_id in valid_uuids:
        pdf = PDF()
        # pdf.alias_nb_pages()
        pdf.add_page()

        # General Result Info
        model_instance_id = result_data[result_id]["model_version_id"]
        model_instance_info = model_catalog.get_model_instance(instance_id=model_instance_id)
        model_id = model_instance_info["model_id"]
        model_info = model_catalog.get_model(model_id=model_id, instances=False, images=False)
        test_instance_id = result_data[result_id]["test_code_id"]
        test_instance_info = test_library.get_test_instance(instance_id=test_instance_id)
        test_id = test_instance_info["test_definition_id"]
        test_info = test_library.get_test_definition(test_id=test_id)
        test_info.pop("codes")

        # pdf.add_page()
        _print_param_value(pdf, "Result UUID: ", result_id, 14)
        # Result Info
        pdf.ln(10)
        pdf.set_font('Arial', 'BU', 14)
        pdf.ln(10)
        pdf.cell(190, 10, 'Result Info', 0, 1, 'C')
        for key, val in result_data[result_id].items():
            _print_param_value(pdf, str(key + ": "), str(val), 12)
            pdf.ln(10)

        # Model Info
        pdf.ln(10)
        pdf.set_font('Arial', 'BU', 14)
        pdf.ln(10)
        pdf.cell(190, 10, 'Model Info', 0, 1, 'C')
        for key, val in model_info.items():
            if key == "app":
                _print_param_value(pdf, "collab_id", str(val["collab_id"]), 12)
                pdf.ln(10)
                _print_param_value(pdf, "app_id", str(val["id"]), 12)
            else:
                _print_param_value(pdf, str(key + ": "), unicodedata.normalize('NFKD', val).encode('ascii','ignore') if isinstance(val, unicode) else str(val), 12)
            pdf.ln(10)

        # Model Instance Info
        pdf.ln(10)
        pdf.set_font('Arial', 'BU', 14)
        pdf.ln(10)
        pdf.cell(190, 10, 'Model Instance Info', 0, 1, 'C')
        for key, val in model_instance_info.items():
            _print_param_value(pdf, str(key + ": "), str(val), 12)
            pdf.ln(10)

        # Test Info
        pdf.ln(10)
        pdf.set_font('Arial', 'BU', 14)
        pdf.ln(10)
        pdf.cell(190, 10, 'Test Info', 0, 1, 'C')
        for key, val in test_info.items():
            _print_param_value(pdf, str(key + ": "), str(val), 12)
            pdf.ln(10)

        # Test Instance Info
        pdf.ln(10)
        pdf.set_font('Arial', 'BU', 14)
        pdf.ln(10)
        pdf.cell(190, 10, 'Test Instance Info', 0, 1, 'C')
        for key, val in test_instance_info.items():
            _print_param_value(pdf, str(key + ": "), str(val), 12)
            pdf.ln(10)

        pdf.output(str("./report/"+filename[:-4]+"_temp_"+str(result_ctr)+".pdf"), 'F')

        # Additional Files
        if result_data[result_id]["results_storage"]:
            datastore = CollabDataStore(auth=model_catalog.auth)
            entity_uuid = datastore._translate_URL_to_UUID(result_data[result_id]["results_storage"])
            file_list = datastore.download_data_using_uuid(entity_uuid)

            merger = PdfFileMerger()
            merger.append(str("./report/"+filename[:-4]+"_temp_"+str(result_ctr)+".pdf"))
            temp_txt_files = []

            for datafile in file_list:
                if datafile.endswith(".pdf"):
                    merger.append(PdfFileReader(file(datafile, 'rb')))
                elif datafile.endswith((".txt", ".json")):
                    txt_pdf = FPDF()
                    txt_pdf.add_page()
                    txt_pdf.set_font('Arial', 'BU', 14)
                    txt_pdf.cell(0, 10, os.path.basename(datafile), 0, 1, 'C')
                    txt_pdf.set_font('Courier', '', 8)
                    with open(datafile, 'r') as txt_file:
                        txt_content = txt_file.read().splitlines()
                    for txt_line in txt_content:
                        txt_pdf.cell(0,0, txt_line)
                        txt_pdf.ln(5)
                    savepath = os.path.join("./report", "temp_"+os.path.splitext(os.path.basename(datafile))[0]+"_"+str(result_ctr)+".pdf")
                    temp_txt_files.append(savepath)
                    txt_pdf.output(str(savepath), 'F')
                    merger.append(PdfFileReader(file(savepath, 'rb')))

            merger.write(str("./report/"+filename[:-4]+"_"+str(result_ctr)+".pdf"))
            os.remove(str("./report/"+filename[:-4]+"_temp_"+str(result_ctr)+".pdf"))
            for tempfile in temp_txt_files:
                os.remove(tempfile)
            result_ctr = result_ctr + 1

    merger = PdfFileMerger()
    merger.append(str("./report/"+filename[:-4]+"_cover.pdf"))
    if only_combined:
        os.remove(str("./report/"+filename[:-4]+"_cover.pdf"))
    for i in range(result_ctr):
        merger.append(str("./report/"+filename[:-4]+"_"+str(i)+".pdf"))
        if only_combined:
            os.remove(str("./report/"+filename[:-4]+"_"+str(i)+".pdf"))
    merger.write(str("./report/"+filename))
    report_path = os.path.abspath("./report/"+filename)
    print("Report generated at: {}".format(report_path))
    return valid_uuids, report_path

def generate_score_matrix(username="", password=None, environment="production", result_list=[], collab_id=None, client_obj=None):
    """Generates a pandas dataframe with score matrix

    This method will generate a pandas dataframe for the specified test results.
    Each row will correspond to a particular model instance, and the columns
    correspond to the test instances.

    Parameters
    ----------
    username : string
        Your HBP collaboratory username.
    environment : string, optional
        Used to indicate whether being used for development/testing purposes.
        Set as `production` as default for using the production system,
        which is appropriate for most users. When set to `dev`, it uses the
        `development` system. For other values, an external config file would
        be read (the latter is currently not implemented).
    result_list : list
        List of result UUIDs for which score matrix is to be generated.
    collab_id : string, optional
        Collaboratory ID where hyperlinks to results are to be redirected.
        If unspecified, the scores will not have clickable hyperlinks.
    client_obj : ModelCatalog/TestLibrary object
        Used to easily create a new ModelCatalog/TestLibrary object if either exist already.
        Avoids need for repeated authentications; improves performance. Also, helps minimize
        being blocked out by the authentication server for repeated authentication requests
        (applicable when running several tests in quick succession, e.g. in a loop).

    Returns
    -------
    pandas.DataFrame
        A 2-dimensional matrix representation of the scores

    Examples
    --------
    >>> result_list = ["a618a6b1-e92e-4ac6-955a-7b8c6859285a", "793e5852-761b-4801-84cb-53af6f6c1acf"]
    >>> df = utils.generate_score_matrix(username="shailesh", result_list=result_list)
    """

    try:
        import pandas as pd
    except ImportError:
        print("Please install the following package: pandas")
        return

    if client_obj:
        model_catalog = ModelCatalog.from_existing(client_obj)
    else:
        model_catalog = ModelCatalog(username, password, environment=environment)

    if client_obj:
        test_library = TestLibrary.from_existing(client_obj)
    else:
        test_library = TestLibrary(username, password, environment=environment)

    if collab_id:
        # check if app exists; if not then create
        VFapp_navID = test_library.exists_in_collab_else_create(collab_id)
        test_library.set_app_config(collab_id=collab_id, app_id=VFapp_navID, only_if_new="True")

    results_dict = collections.OrderedDict()
    models_dict = collections.OrderedDict()
    tests_dict = collections.OrderedDict()

    for uuid in result_list:
        result = test_library.get_result(result_id = uuid)["results"][0]
        if result["test_code_id"] in results_dict.keys():
            results_dict[result["test_code_id"]].update({result["model_version_id"]: str(result["score"]) + "#*#" + uuid}) # '#*#' is used as separator
        else:
            results_dict[result["test_code_id"]] = {result["model_version_id"]: str(result["score"]) + "#*#" + uuid}

        if result["model_version_id"] not in models_dict.keys():
            models_dict[result["model_version_id"]] = None
        if result["test_code_id"] not in models_dict.keys():
            tests_dict[result["test_code_id"]] = None

    # form test labels: test_name(version_name)
    for uuid in tests_dict.keys():
        test = test_library.get_test_instance(instance_id=uuid)
        test_version = test["version"]
        test = test_library.get_test_definition(test_id=test["test_definition_id"])
        test_name = test["alias"] if test["alias"] else test["name"]
        test_label = test_name + " (" + str(test_version) + ")"
        tests_dict[uuid] = test_label

    # form model labels: model_name(version_name)
    for uuid in models_dict.keys():
        model = model_catalog.get_model_instance(instance_id=uuid)
        model_version = model["version"]
        model = model_catalog.get_model(model_id=model["model_id"])
        model_name = model["alias"] if model["alias"] else model["name"]
        model_label = model_name + "(" + str(model_version) + ")"
        models_dict[uuid] = model_label

    data = {}
    for t_key, t_val in tests_dict.items():
        score_vals = []
        for m_key in models_dict.keys():
            try:
                score_vals.append(results_dict[t_key][m_key])
            except KeyError:
                score_vals.append(None)
        data[t_val] = score_vals
    df = pd.DataFrame(data, index = models_dict.values())

    def make_clickable(value):
        if not value:
            return value
        score, result_uuid = value.split('#*#')
        if collab_id:
            result_url = "https://collab.humanbrainproject.eu/#/collab/{}/nav/{}?state=result.{}".format(str(collab_id),str(VFapp_navID), result_uuid)
            return '<a target="_blank" href="{}">{}</a>'.format(result_url,score)
        else:
            return score

    return df.style.format(make_clickable)
