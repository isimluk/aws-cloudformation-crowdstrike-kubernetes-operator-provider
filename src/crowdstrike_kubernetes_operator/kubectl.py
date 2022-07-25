import logging
import os
import re
import yaml
import shlex
import subprocess  # nosec B404
from time import sleep
from kubernetes import client, config, utils
from .utils import run_command

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def login(cluster_name, session=None):
    kubeconfig_location = '.kube.config'
    os.environ["PATH"] = f"/var/task/bin:{os.environ['PATH']}"
    os.environ["PYTHONPATH"] = f"/var/task:{os.environ.get('PYTHONPATH', '')}"
    if session:
        creds = session.client.__self__.get_credentials()
        os.environ["AWS_ACCESS_KEY_ID"] = creds.access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
        os.environ["AWS_SESSION_TOKEN"] = creds.token
    run_command(
        f"aws eks update-kubeconfig --name {cluster_name} --alias {cluster_name} --kubeconfig {kubeconfig_location}",
    )
    config.load_kube_config(config_file=kubeconfig_location)


def run_command(command):
    def log_output(output):
        # CloudWatch PutEvents has a max length limit (256Kb)
        # Use slightly smaller value to include supporting information (timestamp, log level, etc.)
        limit = 260000
        output_string = f"{output}"  # to support dictionaries as arguments
        for m in [output_string[i:i+limit] for i in range(0, len(output_string), limit)]:
            LOG.debug(m)
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


def test():
    v1 = client.CoreV1Api()
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        break


def apply(manifests):
    k8s_client = client.ApiClient()
    return utils.create_from_yaml(k8s_client, yaml_objects=manifests)


def delete(manifests):
    # TODO: delete sensors first
    k8s_client = client.ApiClient()
    for manifest in reversed(manifests):
        LOG.debug(f"deleting manifest: {manifest}")
        delete_from_dict(k8s_client, manifest, verbose=True)


def delete_from_yaml(k8s_client, yaml_content, verbose=False,
                     namespace="default", **kwargs):
    yml_document_all = yaml.safe_load_all(yaml_content)
    failures = []
    for yml_document in yml_document_all:
        try:
            delete_from_dict(k8s_client, yml_document, verbose,
                             namespace=namespace, **kwargs)
        except FailToDeleteError as failure:
            failures.extend(failure.api_exceptions)
    if failures:
        raise FailToDeleteError(failures)


def delete_from_dict(k8s_client, yml_document, verbose,
                     namespace="default", **kwargs):
    api_exceptions = []
    if "List" in yml_document["kind"]:
        kind = yml_document["kind"].replace("List", "")
        for yml_doc in yml_document["items"]:
            if kind != "":
                yml_doc["apiVersion"] = yml_document["apiVersion"]
                yml_doc["kind"] = kind
            try:
                delete_from_yaml_single_item(
                    k8s_client, yml_doc, verbose, namespace=namespace, **kwargs
                )
            except client.rest.ApiException as api_exception:
                api_exceptions.append(api_exception)
    else:
        try:
            delete_from_yaml_single_item(
                k8s_client, yml_document, verbose,
                namespace=namespace, **kwargs
            )
        except client.rest.ApiException as api_exception:
            api_exceptions.append(api_exception)

    if api_exceptions:
        raise FailToDeleteError(api_exceptions)


def delete_from_yaml_single_item(k8s_client,
                                 yml_document, verbose=False, **kwargs):
    # get group and version from apiVersion
    group, _, version = yml_document["apiVersion"].partition("/")
    if version == "":
        version = group
        group = "core"
    # Take care for the case e.g. api_type is "apiextensions.k8s.io"
    group = "".join(group.rsplit(".k8s.io", 1))
    # convert group name from DNS subdomain format to
    # python class name convention
    group = "".join(word.capitalize() for word in group.split('.'))
    func = "{0}{1}Api".format(group, version.capitalize())
    k8s_api = getattr(client, func)(k8s_client)
    kind = yml_document["kind"]
    kind = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', kind)
    kind = re.sub('([a-z0-9])([A-Z])', r'\1_\2', kind).lower()
    if hasattr(k8s_api, "create_namespaced_{0}".format(kind)):
        if "namespace" in yml_document["metadata"]:
            namespace = yml_document["metadata"]["namespace"]
            kwargs["namespace"] = namespace
        name = yml_document["metadata"]["name"]
        res = getattr(k8s_api, "delete_namespaced_{}".format(kind))(
            name=name,
            body=client.V1DeleteOptions(propagation_policy="Background",
                                        grace_period_seconds=5), **kwargs)
    else:
        # get name of object to delete
        name = yml_document["metadata"]["name"]
        kwargs.pop('namespace', None)
        res = getattr(k8s_api, "delete_{}".format(kind))(
            name=name,
            body=client.V1DeleteOptions(propagation_policy="Background",
                                        grace_period_seconds=5), **kwargs)
    if verbose:
        msg = "{0} deleted.".format(kind)
        if hasattr(res, 'status'):
            msg += " status='{0}'".format(str(res.status))
        print(msg)


class FailToDeleteError(Exception):
    def __init__(self, api_exceptions):
        self.api_exceptions = api_exceptions

    def __str__(self):
        msg = ""
        for api_exception in self.api_exceptions:
            msg += "Error from server ({0}):{1}".format(
                api_exception.reason, api_exception.body)
        return msg
