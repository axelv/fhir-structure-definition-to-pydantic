import json
import logging
from pydantic import create_model, BaseModel, parse_file_as, ValidationError
from datetime import datetime, time, date
from typing import Optional, List


### MINIMAL SET OF MODELS NECESSARY TO PARSE FHIR RESOURCES ### 

logging.basicConfig(level=logging.DEBUG, filename="log.txt")

class Identifier(BaseModel):
    pass

class Reference(BaseModel):
    pass

class Extension(BaseModel):
    pass

models = {
    "http://hl7.org/fhirpath/System.String": str,
    "http://hl7.org/fhirpath/System.Integer": int,
    "http://hl7.org/fhirpath/System.Decimal": float,
    "http://hl7.org/fhirpath/System.Boolean": bool,
    "http://hl7.org/fhirpath/System.DateTime": datetime,
    "http://hl7.org/fhirpath/System.Time": time,
    "http://hl7.org/fhirpath/System.Date": date,
    "Extension": Extension,
    "Reference": Reference,
    "Identifier": Identifier,
}

def is_element(element):
    return "type" in element and element["path"]

def extract_type(element):
    match element:
        case {"min": 0, "max": "1"}:
            return (Optional[models[element["type"][0]["code"]]], None)
        case {"min": 0, "max": "*"}:
            return (list[models[element["type"][0]["code"]]], [])
        case {"min": 1, "max": "1"}:
            return  (models[element["type"][0]["code"]], ...)
        case {"min": 1, "max": "*"}:
            return (list[models[element["type"][0]["code"]]], ...)
        case {"min": 0, "max": "0"}:
            return None
    raise ValueError("Unknown min value %s and max value %s" % (element["min"], element["max"]))

def create_primitive(structure_resource):
    logging.debug("Creating model for %s" % structure_resource["id"])
    value_path = structure_resource["id"]  + ".value"
    for element in structure_resource["snapshot"]["element"]:
        if is_element(element):
            if element["max"] == "1":
                type_ = models[element["type"][0]["code"]]
            elif element["max"] == "*":
                type_ = list[models[element["type"][0]["code"]]]
            else:
                raise ValueError("Invalid max value %s for a primitive value" % element["max"])
            return type_
    raise ValueError("Primitive (id=%s) without 'value' element. Searched on path %s."% (structure_resource["id"], value_path))

def create_complex_type(structure_resource):
    logging.debug("Creating model for %s" % structure_resource["id"])
    fields = {}
    for element in structure_resource["snapshot"]["element"]:
        field_name = element["path"].split(".")[-1]
        if is_element(element):
            type_ = extract_type(element)
            if type_ is None:
                continue
            fields[field_name] = type_
    return create_model(structure_resource["id"], **fields)

def create_resource(structure_resource):
    logging.debug("Creating model for %s" % structure_resource["id"])
    fields = {}
    for element in structure_resource["snapshot"]["element"]:
        path = element["path"].split(".")
        if len(path) == 1:
            continue
        if len(path) > 2:
            logging.warning("Nested elements are not supported. Skipping %s" % element["path"])
            continue
        field_name = path[1]
        if is_element(element):
            type_ = extract_type(element)
            if type_ is None:
                continue
            fields[field_name] = type_
    return create_model(structure_resource["id"], **fields.copy())

# This is a hack to get around the fact that the FHIR definitions are not in a valid order
# and some models reference other models that are not yet defined.
retries = {}
    
with open("./fhir-definitions/profiles-types.json", "r") as f:
    data = json.load(f)
    entries:list = data["entry"] 
    while len(entries) > 0:
        entry = entries.pop(0)
        structure_resource = entry["resource"].copy()
        if not structure_resource["resourceType"] == "StructureDefinition":
            logging.info("Skipping %s" % structure_resource["resourceType"])
            continue
        structure_id = structure_resource["id"]
        structure_kind = structure_resource["kind"]
        if not "snapshot" in structure_resource:
            logging.info("Skipping %s because it has no snapshot" % structure_id)
            continue
        try:
            if structure_kind == "primitive-type":
                if structure_id in models:
                    continue # already defined
                models[structure_id] = create_primitive(structure_resource)
            elif structure_kind == "complex-type":
                models[structure_id] = create_complex_type(structure_resource)
        except KeyError as e:
            logging.info("Failed to create model for %s because '%s' is missing. Retrying later." % (structure_id, e.args[0]))
            retries[structure_id] = retries.get(structure_id, 0) + 1
            if retries[structure_id] < 5:
                entries.append(entry)
            else:
                logging.warning("Failed to create model for %s" % structure_id)
        except ValueError as e:
            logging.warning("Failed to create model for %s" % structure_id, exc_info=e)

with open("./fhir-definitions/profiles-resources.json", "r") as f:
    data = json.load(f)
    entries:list = data["entry"] 
    while len(entries) > 0:
        entry = entries.pop(0)
        structure_resource = entry["resource"].copy()
        if not structure_resource["resourceType"] == "StructureDefinition":
            logging.info("Skipping %s" % structure_resource["resourceType"])
            continue
        structure_id = structure_resource["id"]
        structure_kind = structure_resource["kind"]
        if not "snapshot" in structure_resource:
            logging.info("Skipping %s because it has no snapshot" % structure_id)
            continue
        try:
            if structure_kind == "resource":
                models[structure_id] = create_resource(structure_resource)
            else:
                logging.warning("Unknown structure kind %s" % structure_kind)
        except KeyError as e:
            logging.info("Failed to create model for %s because '%s' is missing. Retrying later." % (structure_id, e.args[0]))
            retries[structure_id] = retries.get(structure_id, 0) + 1
            if retries[structure_id] < 5:
                entries.append(entry)
            else:
                logging.warning("Failed to create model for %s" % structure_id)
        except ValueError as e:
            logging.warning("Failed to create model for %s" % structure_id, exc_info=e)

## Test
errors = []
try:
    patient = parse_file_as(models["Patient"], "test-resources/patient.json")
    with open("test-resources/patient-parsed.json", "w") as f:
        f.write(patient.json(exclude_unset=True)) 
except ValidationError as e:
    errors.append(e)
try:
    observation = parse_file_as(models["Observation"], "test-resources/observation.json")
    with open("test-resources/observation-parsed.json", "w") as f:
        f.write(observation.json(exclude_unset=True))
except ValidationError as e:
    errors.append(e)

print(errors)
