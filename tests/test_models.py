import pytest
import platform
import uuid
from datetime import datetime
from time import sleep

"""
1] Retrieve a model description by its model_id or alias.
"""

#1.1) Without model_id or alias
def test_getModel_none(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model = model_catalog.get_model()
    assert str(excinfo.value) == "Model ID or alias needs to be provided for finding a model."

#1.2) Using model_id
def test_getModel_id(modelCatalog, myModelID):
    model_catalog = modelCatalog
    model_id = myModelID
    model = model_catalog.get_model(model_id=model_id)
    assert model["id"] ==  model_id

#1.3) Using alias
def test_getModel_alias(modelCatalog, myModelID):
    sleep(60)  # time for KG indexing
    model_catalog = modelCatalog
    model_id = myModelID
    model = model_catalog.get_model(model_id=model_id)
    model = model_catalog.get_model(alias=model["alias"])
    assert model["id"] ==  model_id

#1.4) Using model_id and alias
def test_getModel_both(modelCatalog, myModelID):
    model_catalog = modelCatalog
    model_id = myModelID
    model = model_catalog.get_model(model_id=model_id)
    model = model_catalog.get_model(model_id=model_id, alias=model["alias"])
    assert model["id"] ==  model_id

#1.5) Using invalid model_id format
def test_getModel_invalid_id_format(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model = model_catalog.get_model(model_id="abcde")
    assert "Error in retrieving model." in str(excinfo.value)

#1.6) Using invalid model_id value
def test_getModel_invalid_id_value(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model = model_catalog.get_model(model_id=str(uuid.uuid4()))
    assert "Error in retrieving model." in str(excinfo.value)

#1.7) Using invalid alias
def test_getModel_invalid_alias(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model = model_catalog.get_model(alias="<>(@#%^)")
    assert "Error in retrieving model." in str(excinfo.value)

#1.8) Using empty model_id
def test_getModel_empty_id(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model = model_catalog.get_model(model_id="")
    assert "Model ID or alias needs to be provided for finding a model." in str(excinfo.value)

#1.9) Using empty alias
def test_getModel_empty_alias(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model = model_catalog.get_model(alias="")
    assert "Model ID or alias needs to be provided for finding a model." in str(excinfo.value)

#1.10) Hide instances
def test_getModel_hide_instances(modelCatalog, myModelID):
    model_catalog = modelCatalog
    model_id = myModelID
    model = model_catalog.get_model(model_id=model_id, instances=False)
    assert "instances" not in model.keys()

#1.11) Hide images
def test_getModel_hide_images(modelCatalog, myModelID):
    model_catalog = modelCatalog
    model_id = myModelID
    model = model_catalog.get_model(model_id=model_id, images=False)
    assert "images" not in model.keys()


"""
2] List models satisfying all specified filters
"""

#2.1) No filters
@pytest.mark.skip  # skip because it takes too long to get all models. Just get first 100?
def test_getList_no_filter(modelCatalog):
    model_catalog = modelCatalog
    models = model_catalog.list_models()
    assert isinstance(models, list)
    assert len(models) > 0

#2.2) Single filter
def test_getList_one_filter(modelCatalog, myModelID):
    model_catalog = modelCatalog
    models = model_catalog.list_models(collab_id="model-validation")
    assert isinstance(models, list)
    assert len(models) > 0
    collab_ids = set([model["project_id"] for model in models])
    assert len(collab_ids) == 1
    value, = collab_ids
    assert value == "model-validation"

#2.3) Multiple filters
def test_getList_many_filters(modelCatalog, myModelID):
    model_catalog = modelCatalog
    models = model_catalog.list_models(cell_type="medium spiny neuron",
                                       brain_region="striatum")
    assert isinstance(models, list)
    assert len(models) > 0

#2.4) Invalid filter
def test_getList_invalid_filter(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        models = model_catalog.list_models(abcde="12345")
    assert "The specified filter 'abcde' is an invalid filter!" in str(excinfo.value)

#2.5) Filter with no matches
def test_getList_nomatch(modelCatalog):
    model_catalog = modelCatalog
    #models = model_catalog.list_models(app_id="ABCDE")
    models = model_catalog.list_models(species="Ornithorhynchus anatinus",
                                       brain_region="retina")
    assert isinstance(models, list)
    assert len(models) == 0


"""
3] Display list of valid values for fields
"""

#3.1) No parameters (all)
def test_getModelValid_none(modelCatalog):
    model_catalog = modelCatalog
    data = model_catalog.get_attribute_options()
    assert isinstance(data, dict)
    assert len(data.keys()) > 0

#3.2) One parameter
def test_getModelValid_one(modelCatalog):
    model_catalog = modelCatalog
    data = model_catalog.get_attribute_options("cell_type")
    assert isinstance(data, dict)
    assert len(data.keys()) == 1
    assert "cell_type" in data.keys()
    assert isinstance(data["cell_type"], list)
    assert len(data["cell_type"]) > 0

#3.3) Multiple parameters
def test_getModelValid_many(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(TypeError) as excinfo:
        data = model_catalog.get_attribute_options("cell_type", "brain_region")
    assert "takes at most 2 arguments" in str(excinfo.value) or "takes from 1 to 2 positional arguments" in str(excinfo.value)

#3.4) Invalid parameter
def test_getModelValid_invalid(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        data = model_catalog.get_attribute_options("abcde")
    assert "Specified attribute 'abcde' is invalid." in str(excinfo.value)

"""
4] Register a new model on the model catalog
"""

#4.1) No parameters
def test_addModel_none(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model_id = model_catalog.register_model()

#4.2) Missing mandatory parameter (author)
def test_addModel_missingParam(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model_name = "Model_{}_{}_py{}_add2".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
        model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                       alias=model_name, organization="HBP-SP6",
                       private=False, cell_type="granule cell", model_scope="single cell",
                       abstraction_level="spiking neurons",
                       brain_region="basal ganglia", species="Mus musculus",
                       owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                       description="This is a test entry! Please ignore.")
    assert "field required" in str(excinfo.value)  # author is missing

#4.3) Invalid value for parameter (brain_region)
def test_addModel_invalidParam(modelCatalog):
    model_catalog = modelCatalog
    with pytest.raises(Exception) as excinfo:
        model_name = "Model_{}_{}_py{}_add3".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
        model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                       alias=model_name, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                       private=False, cell_type="granule cell", model_scope="single cell",
                       abstraction_level="spiking neurons",
                       brain_region="ABCDE", species="Mus musculus",
                       owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                       description="This is a test entry! Please ignore.")
    assert "brain_region = 'ABCDE' is invalid." in str(excinfo.value)

#4.4) Valid model without alias; without instances and images
def test_addModel_valid_noalias_nodetails(modelCatalog):
    model_catalog = modelCatalog
    model_name = "Model_{}_{}_py{}_add4".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                   author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.")
    assert isinstance(uuid.UUID(model_id, version=4), uuid.UUID)

#4.5) Valid model with alias; without instances and images
def test_addModel_valid_withalias_nodetails(modelCatalog):
    model_catalog = modelCatalog
    model_name = "Model_{}_{}_py{}_add5".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                   alias=model_name, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.")
    assert isinstance(uuid.UUID(model_id, version=4), uuid.UUID)

#4.6) Invalid model with repeated alias; without instances and images
def test_addModel_repeat_alias_nodetails(modelCatalog):
    model_catalog = modelCatalog
    model_name = "Model_{}_{}_py{}_add6".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                   alias=model_name, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.")
    sleep(30)
    with pytest.raises(Exception) as excinfo:
        model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                       alias=model_name, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                       private=False, cell_type="granule cell", model_scope="single cell",
                       abstraction_level="spiking neurons",
                       brain_region="basal ganglia", species="Mus musculus",
                       owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                       description="This is a test entry! Please ignore.")
    assert "already exists." in str(excinfo.value)

#4.7) Valid model with alias; with instances and images
# Note: using current timestamp as alias to ensure uniqueness
def test_addModel_valid_withalias_withdetails(modelCatalog):
    model_catalog = modelCatalog
    model_name = "Model_{}_{}_py{}_add7".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                   alias=model_name, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.",
                   instances=[{"source":"https://www.abcde.com",
                               "version":"1.0", "parameters":""},
                              {"source":"https://www.12345.com",
                               "version":"2.0", "parameters":""}],
                   images=[{"url":"http://www.neuron.yale.edu/neuron/sites/default/themes/xchameleon/logo.png",
                            "caption":"NEURON Logo"},
                           {"url":"https://collab.humanbrainproject.eu/assets/hbp_diamond_120.png",
                            "caption":"HBP Logo"}])
    assert isinstance(uuid.UUID(model_id, version=4), uuid.UUID)


"""
5] Edit an existing model on the model catalog
"""

#5.1) Invalid change - no model_id
def test_editModel_invalid_noID(modelCatalog):
    model_catalog = modelCatalog
    model_name = "Model_{}_{}_py{}_edit1".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                   alias=model_name, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.")
    model = model_catalog.get_model(model_id=model_id)
    with pytest.raises(Exception) as excinfo:
        model_id = model_catalog.edit_model(
                       collab_id="model-validation", name=model["name"] + "_changed",
                       alias = model["alias"] + "_changed",
                       author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                       private=False, cell_type="granule cell", model_scope="single cell",
                       abstraction_level="spiking neurons",
                       brain_region="basal ganglia", species="Mus musculus",
                       owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                       description="This is a test entry! Please ignore.")
    assert str(excinfo.value) == "Model ID needs to be provided for editing a model."

#5.2) Valid change - model_id
def test_editModel_valid(modelCatalog):
    model_catalog = modelCatalog
    model_name = "Model_{}_{}_py{}_edit2".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name,
                   alias=model_name, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.")
    model = model_catalog.get_model(model_id=model_id)
    model_id = model_catalog.edit_model(model_id=model_id,
                   collab_id="model-validation", name=model["name"] + "_changed",
                   alias = model["alias"] + "_changed", author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP4",
                   private=False, cell_type="pyramidal cell", model_scope="network: whole brain",
                   abstraction_level="systems biology",
                   brain_region="hippocampus", species="Rattus norvegicus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="HBP SP 6.4", license="BSD 2-Clause",
                   description="This is a test entry! Please ignore.")
    assert isinstance(uuid.UUID(model_id, version=4), uuid.UUID)

#5.3) Invalid change - duplicate alias
def test_editModel_invalid_duplicate_alias(modelCatalog):
    model_catalog = modelCatalog
    model_name1 = "Model_{}_{}_py{}_edit3.1".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name1,
                   alias=model_name1, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.")
    model_name2 = "Model_{}_{}_py{}_edit3.2".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), model_catalog.environment, platform.python_version())
    model_id = model_catalog.register_model(collab_id="model-validation", name="IGNORE - Test Model - " + model_name2,
                   alias=model_name2, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                   private=False, cell_type="granule cell", model_scope="single cell",
                   abstraction_level="spiking neurons",
                   brain_region="basal ganglia", species="Mus musculus",
                   owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                   description="This is a test entry! Please ignore.")
    sleep(20)
    model = model_catalog.get_model(model_id=model_id)
    with pytest.raises(Exception) as excinfo:
        model_id = model_catalog.edit_model(model_id=model_id,
                       collab_id="model-validation", name=model["name"] + "_changed",
                       alias = model_name1, author={"family_name": "Tester", "given_name": "Validation"}, organization="HBP-SP6",
                       private=False, cell_type="granule cell", model_scope="single cell",
                       abstraction_level="spiking neurons",
                       brain_region="basal ganglia", species="Mus musculus",
                       owner={"family_name": "Tester", "given_name": "Validation"}, project="SP 6.4", license="BSD 3-Clause",
                       description="This is a test entry! Please ignore.")
    assert "already exists" in str(excinfo.value)
