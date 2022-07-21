import logging
import os
import re
import yaml
from kubernetes import client, config, utils

LOG = logging.getLogger(__name__)
TYPE_NAME = "CrowdStrike::Kubernetes::Operator"
LOG.setLevel(logging.DEBUG)


def login(cluster_name):
    os.environ["PATH"] = f"/var/task/bin:{os.environ['PATH']}"
    os.environ["PYTHONPATH"] = f"/var/task:{os.environ.get('PYTHONPATH', '')}"
    os.environ["KUBECONFIG"] = "/tmp/kube.config"
    os.environ["KUBE_CONFIG_DEFAULT_LOCATION"] = "/tmp/kube.config"
    if session:
        creds = session.client.__self__.get_credentials()
        os.environ["AWS_ACCESS_KEY_ID"] = creds.access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
        os.environ["AWS_SESSION_TOKEN"] = creds.token
    run_command(
        f"aws eks update-kubeconfig --name {cluster_name} --alias {cluster_name} --kubeconfig /tmp/kube.config",
        None,
        None,
    )
    from . import kubectl
    kubectl.test()

def test():
    # Configs can be set in Configuration class directly or using helper utility
    config.load_kube_config()
    v1 = client.CoreV1Api()
    LOG.debug("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        LOG.debug("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


def apply(manifest):
    config.load_kube_config()
    k8s_client = client.ApiClient()
    return utils.create_from_yaml(k8s_client, manifest)


def delete(manifest):
    config.load_kube_config()
    k8s_client = client.ApiClient()
    delete_from_yaml(k8s_client, manifest)


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
