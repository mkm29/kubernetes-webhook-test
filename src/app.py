import base64
import copy
import http
import json
import random

import jsonpatch
from flask import Flask, jsonify, request

app = Flask(__name__)

LABEL = "com.rtx.dataplatform.security"


def has_security_context(spec) -> bool:
    if spec["request"]["object"]["spec"]["template"]["spec"].get("securityContext"):
        return True, "Security Context set at pod level"
    container_scc = False
    for container in spec["request"]["object"]["spec"]["template"]["spec"][
        "containers"
    ]:
        if not container.get("securityContext"):
            container_scc = True
        if not container_scc:
            return True, "Security Context set at container level"
    return False, "No security context found in deployment"


@app.route("/validate", methods=["POST"])
def validate():
    request_info = request.get_json()
    print("Recieved request (validating): {}".format(request_info))
    uid = request_info["request"].get("uid")

    if request_info["request"]["object"]["metadata"]["labels"].get(LABEL):
        app.logger.info(
            f'Object {request_info["request"]["object"]["kind"]}/{request_info["request"]["object"]["metadata"]["name"]} contains the required "{LABEL}" label. Allowing the request.'
        )

        return admission_response(True, uid, f"{LABEL} label exists.")
    else:
        app.logger.error(
            f'Object {request_info["request"]["object"]["kind"]}/{request_info["request"]["object"]["metadata"]["name"]} doesn\'t have the required "{LABEL}" label. Request rejected!'
        )

        return admission_response(False, uid, f'The label "{LABEL}" isn\'t set!')


def admission_response(allowed, uid, message):
    return jsonify(
        {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "allowed": allowed,
                "uid": uid,
                "status": {"message": message},
            },
        }
    )


@app.route("/mutate", methods=["POST"])
def mutate():
    spec = request.json["request"]["object"]
    modified_spec = copy.deepcopy(spec)

    try:
        modified_spec["metadata"]["labels"]["example.com/new-label"] = str(
            random.randint(1, 1000)
        )
    except KeyError:
        pass
    patch = jsonpatch.JsonPatch.from_diff(spec, modified_spec)
    return jsonify(
        {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "allowed": True,
                "uid": request.json["request"]["uid"],
                "patch": base64.b64encode(str(patch).encode()).decode(),
                "patchtype": "JSONPatch",
            },
        }
    )


@app.route("/home")
def home():
    return jsonify({"message": "Hello World!"})


@app.route("/health", methods=["GET"])
def health():
    return ("", http.HTTPStatus.NO_CONTENT)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)  # pragma: no cover
