"""
Miscellaneous methods that help in different aspects of model validation.
Does not require explicit instantiation.

The following methods are available:

====================================   ====================================
Action                                 Method
====================================   ====================================
View JSON data in web browser          :meth:`view_json_tree`
Run test and register result           :meth:`run_test`
Download PDF report of test results    :meth:`generate_report`
====================================   ====================================
"""

import os
import json
import webbrowser
import argparse
try:
    raw_input
except NameError:  # Python 3
    raw_input = input
import sciunit
from datetime import datetime
from . import TestLibrary, ModelCatalog
from .datastores import CollabDataStore
from fpdf import FPDF
from PyPDF2 import PdfFileMerger, PdfFileReader

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

def run_test(hbp_username="", environment="production", model="", test_instance_id="", test_id="", test_alias="", test_version="", storage_collab_id="", register_result=True, model_metadata="", **test_kwargs):
    """Run validation test and register result

    This method will accept a model, located locally, run the specified
    test on the model, and store the results on the validation service.
    The test can be specified in the following ways (in order of priority):

    1. specify `test_instance_id` corresponding to test instance in test library
    2. specify `test_id` and `test_version`
    3. specify `test_alias` and `test_version`

    Parameters
    ----------
    hbp_username : string
        Your HBP collaboratory username.
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
        Collab ID where output files should be stored; if empty, stored in model's host collab.
    register_result : boolean
        Specify whether the test results are to be scored on the validation framework.
        Default is set as True.
    model_metadata : dict
        Data for registering model in the model catalog. If the model already exists
        in the model catalog, then the model_instance UUID must be specified in the model's source
        code by setting `model.instance_id`. Otherwise, the model is registered using info from
        `model_metadata`. If `id` and `model_metadata` are both absent, then the results
        will not be saved on the validation framework (even if `register_result` = True).
    **test_kwargs : list
        Keyword arguments to be passed to the Test constructor.

    Note
    ----
    This is a very basic implementation that would suffice for simple use cases.
    You can customize and create your own run_test() implementations.

    Returns
    -------
    UUID
        UUID of the test result that has been created.

    Examples
    --------
    >>> import models
    >>> from hbp_validation_framework import utils
    >>> mymodel = models.hippoCircuit()
    >>> utils.run_test(hbp_username="shailesh", model=mymodel, test_alias="CDT-5", test_version="5.0")
    """

    # Check the model
    if not isinstance(model, sciunit.Model):
        raise TypeError("`model` is not a sciunit Model!")
    print("----------------------------------------------")
    print("Model name: ", model)
    print("Model type: ", type(model))
    print("----------------------------------------------")

    if not hbp_username:
        print("\n==============================================")
        print("Please enter your HBP username.")
        hbp_username = raw_input('HBP Username: ')

    # Load the test
    test_library = TestLibrary(hbp_username, environment=environment)

    if test_instance_id == "" and (test_id == "" or test_version == "") and (test_alias == "" or test_version == ""):
        raise Exception("test_instance_id or (test_id, test_version) or (test_alias, test_version) needs to be provided for finding test.")
    else:
        test = test_library.get_validation_test(instance_id=test_instance_id, test_id=test_id, alias=test_alias, version=test_version, **test_kwargs)

    print("----------------------------------------------")
    print("Test name: ", test)
    print("Test type: ", type(test))
    print("----------------------------------------------")

    # Run the test
    score = test.judge(model, deep_error=True)
    print("----------------------------------------------")
    print("Score: ", score
    if "figures" in score.related_data:
        print("Output files: ")
        for item in score.related_data["figures"]:
            print(item)
    print("----------------------------------------------")

    if register_result:
        # Register the result with the HBP Validation service
        model_catalog = ModelCatalog(hbp_username, environment=environment)
        if not hasattr(score.model, 'instance_id') and not model_metadata:
            print("Model = ", model, " => Results NOT saved on validation framework: no model.instance_id or model_metadata provided!")
        elif not hasattr(score.model, 'instance_id'):
            # If model instance_id not specified, register the model on the validation framework
            model_id = model_catalog.register_model(app_id=model_metadata["app_id"],
                                                    name=model_metadata["name"] if "name" in model_metadata else model.name,
                                                    alias=model_metadata["alias"] if "alias" in model_metadata else None,
                                                    author=model_metadata["author"],
                                                    organization=model_metadata["organization"],
                                                    private=model_metadata["private"],
                                                    cell_type=model_metadata["cell_type"],
                                                    model_type=model_metadata["model_type"],
                                                    brain_region=model_metadata["brain_region"],
                                                    species=model_metadata["species"],
                                                    description=model_metadata["description"],
                                                    instances=model_metadata["instances"])
            model_instance_id = model_catalog.get_model_instance(model_id=model_id["uuid"], version=model_metadata["instances"][0]["version"])
            score.model.instance_id = model_instance_id["id"]

        model_instance_json = model_catalog.get_model_instance(instance_id=score.model.instance_id)
        model_json = model_catalog.get_model(model_id=model_instance_json["model_id"])
        model_host_collab_id = model_json["app"]["collab_id"]
        model_name = model_json["name"]

        if not storage_collab_id:
            storage_collab_id = model_host_collab_id
            score.related_data["project"] = storage_collab_id
        #     print "=============================================="
        #     print "Enter Collab ID for Data Storage (if applicable)"
        #     print "(Leave empty for Model's host collab, i.e. ", model_host_collab_id, ")"
        #     score.related_data["project"] = raw_input('Collab ID: ')

        collab_folder = "{}_{}".format(model_name, datetime.now().strftime("%Y%m%d-%H%M%S"))
        collab_storage = CollabDataStore(collab_id=storage_collab_id,
                                         base_folder=collab_folder,
                                         auth=test_library.auth)

        response = test_library.register_result(test_result=score, data_store=collab_storage)
        # response = test_library.register_result(test_result=score)
        return response

def generate_report(hbp_username="", environment="production", result_list=[], only_combined=True):
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
    hbp_username : string
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

    Returns
    -------
    list
        List of valid UUIDs for which the PDF report was generated.

    Examples
    --------
    >>> result_list = ["a618a6b1-e92e-4ac6-955a-7b8c6859285a", "793e5852-761b-4801-84cb-53af6f6c1acf"]
    >>> valid_uuids = utils.generate_report(hbp_username="shailesh", result_list=result_list)
    """
    # This method can be significantly improved in future.

    model_catalog = ModelCatalog(hbp_username, environment=environment)
    test_library = TestLibrary(hbp_username, environment=environment)
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
                    _print_param_value(pdf, str(key + ": "), str(val), 12)
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
            storage_uuid = test_library._translate_URL_to_UUID(result_data[result_id]["results_storage"])
            file_list = test_library._download_resource(storage_uuid)

            merger = PdfFileMerger()
            merger.append(str("./report/"+filename[:-4]+"_temp_"+str(result_ctr)+".pdf"))
            for datafile in file_list:
                if datafile.endswith(".pdf"):
                    merger.append(PdfFileReader(file(datafile, 'rb')))
            merger.write(str("./report/"+filename[:-4]+"_"+str(result_ctr)+".pdf"))
            os.remove(str("./report/"+filename[:-4]+"_temp_"+str(result_ctr)+".pdf"))
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
    print("Report generated at: ", os.path.abspath("./report/"+filename))
    return valid_uuids


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
