import logging
from kubernetes import client, config

LOG = logging.getLogger(__name__)
TYPE_NAME = "CrowdStrike::Kubernetes::Operator"
LOG.setLevel(logging.DEBUG)


def test_kubectl():
    # Configs can be set in Configuration class directly or using helper utility
    config.load_kube_config()
    v1 = client.CoreV1Api()
    LOG.debug("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        LOG.debug("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
