import base64
import copy
import http
import json
import random

import jsonpatch
from flask import Flask, jsonify, request

app = Flask(__name__)

LABEL = "com.rtx.dataplatform.security"


def has_security_context(kind: str, spec: dict) -> bool:
    app.logger.info("Checking for security context on %s", kind)
    match kind:
        case "Deployment", "ReplicaSet", "ReplicationController", "StatefulSet":
            # Do we want to include DaemonSet in here?
            has_scc: bool = False
            for container in spec["template"]["spec"]["containers"]:
                if (
                    "securityContext" in container
                    and "runAsNonRoot" in container["securityContext"].keys()
                ):
                    has_scc = True
            return has_scc
            # return "template" in spec and "spec" in spec["template"] and "securityContext" in spec["template"]["spec"]
        case "Pod":
            return "spec" in spec and "securityContext" in spec["spec"]
        case _:
            # app.logger.info(f"Unhandled kind: {kind}")
            return True


@app.route("/validate", methods=["POST"])
def validate():
    request_info = request.get_json()
    uid = request_info["request"].get("uid")
    app.logger.info(f"Received request to validate UID: {uid}")
    spec = request_info["request"]["object"]
    kind = spec["kind"]
    if kind in ("Pod", "Deployment", "ReplicaSet", "ReplicationController"):
        has_scc = has_security_context(kind, spec)
        if has_scc:
            app.logger.info(f"{uid} has security context")
            return admission_response(
                True, uid, "Resource has securityContext.runAsNotRoot set."
            )
        else:
            app.logger.info(f"{uid} does not have security context")
            return admission_response(
                False, uid, "Resource does not have securityContext.runAsNotRoot set."
            )
    else:
        app.logger.info(
            f"{uid} is not a Pod, Deployment, ReplicaSet, or ReplicationController"
        )
        return admission_response(
            True,
            uid,
            "Resource is not a Pod, Deployment, ReplicaSet, or ReplicationController",
        )


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
    request_info = request.get_json()
    uid = request_info["request"].get("uid")
    app.logger.info(f"Received request to validate UID: {uid}")
    spec = request_info["request"]["object"]
    kind = spec["kind"]
    spec = request.json["request"]["object"]

    if kind in ("Pod", "Deployment", "ReplicaSet", "ReplicationController"):
        has_scc = has_security_context(kind, spec)
        if has_scc:
            app.logger.info(f"{kind}: {uid} has security context")
            return jsonify(
                {
                    "apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "response": {
                        "allowed": True,
                        "uid": request.json["request"]["uid"],
                    },
                }
            )
        else:
            app.logger.info(f"{kind}: {uid} does not have security context")
            # add securitContext.runAsNonRoot to spec

            modified_spec = copy.deepcopy(spec)
            match kind:
                case "Pod":
                    modified_spec["spec"]["securityContext"] = {"runAsNonRoot": True}
                case "Deployment", "ReplicaSet", "ReplicationController":
                    modified_spec["template"]["spec"]["securityContext"] = {
                        "runAsNonRoot": True
                    }
                case _:
                    app.logger.info(f"Unhandled kind: {kind}")
            patch = jsonpatch.JsonPatch.from_diff(spec, modified_spec)
            return jsonify(
                {
                    "apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "response": {
                        "allowed": True,
                        "status": {"message": "Adding security context to object"},
                        "uid": request.json["request"]["uid"],
                        "patch": base64.b64encode(str(patch).encode()).decode(),
                        "patchType": "JSONPatch",
                    },
                }
            )
    else:
        app.logger.info(
            f"{uid} is not a Pod, Deployment, ReplicaSet, or ReplicationController"
        )
        return jsonify(
            {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "allowed": True,
                    "uid": request.json["request"]["uid"],
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
