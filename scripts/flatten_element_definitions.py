import json
from pydantic import create_model

with open("./fhir-definitions/profiles-types.json", "r") as f:
    data = json.load(f)
    for type_i,entry in enumerate(data["entry"]):

        structure_resource = entry["resource"]
        structure_id = structure_resource["id"]
        if not "snapshot" in structure_resource:
            continue
        with open(f"./fhir-definitions-types-csv/{type_i}-{structure_id}.csv", "w") as f:
            f.write("path,min,max,type\n")
            for element in structure_resource["snapshot"]["element"]:
                if not "type" in element:
                    continue
                f.write(",".join((element["path"], str(element["min"]), str(element["max"]), ";".join([type_["code"] for type_ in element["type"]])))+"\n")

with open("./fhir-definitions/profiles-resources.json", "r") as f:
    data = json.load(f)
    for resource_i,entry in enumerate(data["entry"]):

        structure_resource = entry["resource"]
        structure_id = structure_resource["id"]
        if not "snapshot" in structure_resource:
            continue
        with open(f"./fhir-definitions-resources-csv/{resource_i}-{structure_id}.csv", "w") as f:
            f.write("path,min,max,type\n")
            for element in structure_resource["snapshot"]["element"]:
                if not "type" in element:
                    continue
                f.write(",".join((element["path"], str(element["min"]), str(element["max"]), ";".join([type_["code"] for type_ in element["type"]])))+"\n")
