import base64
import logging
import requests
from ruamel import yaml
from . import kubectl


URL = 'https://raw.githubusercontent.com/CrowdStrike/falcon-operator/maint-0.5/deploy/falcon-operator.yaml'
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def encode_id(client_token, cluster_name):
    return base64.b64encode(
        f"{client_token}|{cluster_name}".encode("utf-8")
    ).decode("utf-8")


def handler_init(model, session, stack_name, token):
    kubectl.login(model.ClusterName, session)
    kubectl.test()

    manifest_str = http_get(URL)
    manifests = []

    input_yaml = list(yaml.safe_load_all(manifest_str))
    for manifest in input_yaml:
        add_idempotency_token(manifest, token)
        manifests.append(manifest)
    return manifests


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
