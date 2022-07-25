import base64
import logging
import json
import requests
import shlex
import subprocess
from datetime import datetime, date
from ruamel import yaml
from time import sleep


URL = 'https://raw.githubusercontent.com/CrowdStrike/falcon-operator/maint-0.5/deploy/falcon-operator.yaml'
LOG = logging.getLogger(__name__)
TYPE_NAME = "CrowdStrike::Kubernetes::Operator"
LOG.setLevel(logging.DEBUG)


def encode_id(client_token, cluster_name):
    return base64.b64encode(
        f"{client_token}|{cluster_name}".encode("utf-8")
    ).decode("utf-8")


def handler_init(model, session, stack_name, token):
    physical_resource_id = None

    from . import kubectl
    kubectl.login(model.ClusterName, session)
    kubectl.test()

    manifest_str = http_get(URL)
    manifests = []

    input_yaml = list(yaml.safe_load_all(manifest_str))
    for manifest in input_yaml:
        add_idempotency_token(manifest, token)
        manifests.append(manifest)
    return manifests


def run_command(command, cluster_name, session):
    retries = 0
    while True:
        try:
            try:
                LOG.debug("executing command: %s" % command)
                output = subprocess.check_output(
                    shlex.split(command), stderr=subprocess.STDOUT
                ).decode("utf-8")
                log_output(output)
            except subprocess.CalledProcessError as exc:
                LOG.error(
                    "Command failed with exit code %s, stderr: %s"
                    % (exc.returncode, exc.output.decode("utf-8"))
                )
                raise Exception(exc.output.decode("utf-8"))
            return output
        except Exception as e:
            if "Unable to connect to the server" not in str(e) or retries >= 5:
                raise
            LOG.debug("{}, retrying in 5 seconds".format(e))
            sleep(5)
            retries += 1


def http_get(url):
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch CustomValueYaml url {url}: {e}")
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch CustomValueYaml url {url}: [{response.status_code}] "
            f"{response.reason}"
        )
    return response.text


def add_idempotency_token(manifest, token):
    if "metadata" not in manifest:
        manifest["metadata"] = {}
    if not manifest.get("metadata", {}).get("annotations"):
        manifest["metadata"]["annotations"] = {}
    manifest["metadata"]["annotations"]["cfn-client-token"] = token


def log_output(output):
    # CloudWatch PutEvents has a max length limit (256Kb)
    # Use slightly smaller value to include supporting information (timestamp, log level, etc.)
    limit = 260000
    output_string = f"{output}"  # to support dictionaries as arguments
    for m in [output_string[i:i+limit] for i in range(0, len(output_string), limit)]:
        LOG.debug(m)
