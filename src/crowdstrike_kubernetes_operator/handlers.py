import logging
import kubernetes.utils
from typing import Any, MutableMapping, Optional

from cloudformation_cli_python_lib import (
    Action,
    OperationStatus,
    ProgressEvent,
    Resource,
    SessionProxy,
    exceptions,
)

from .models import ResourceHandlerRequest, ResourceModel
from .utils import encode_id, get_model, handler_init
from . import kubectl

# Use this logger to forward log messages to CloudWatch Logs.
LOG = logging.getLogger(__name__)
TYPE_NAME = "CrowdStrike::Kubernetes::Operator"
LOG.setLevel(logging.DEBUG)

resource = Resource(TYPE_NAME, ResourceModel)
test_entrypoint = resource.test_entrypoint


@resource.handler(Action.CREATE)
def create_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
    )

    LOG.debug(f"Create invoke \n\n{request.__dict__}\n\n{callback_context}")
    physical_resource_id, _, manifest_list = handler_init(
        model, session, request.logicalResourceIdentifier, request.clientRequestToken
    )
    model.CfnId = encode_id(
        request.clientRequestToken,
        model.ClusterName,
    )
    if not callback_context:
        LOG.debug("1st invoke")
        progress.callbackDelaySeconds = 1
        progress.callbackContext = {"init": "complete"}
        return progress

    try:
        kubectl.apply(manifest_list)
    except kubernetes.utils.FailToCreateError as e:
        LOG.debug("FAILED TO CREATE KUBERNETES ERROR")
        LOG.debug(f"exception caught class: {e.__class__}")
        LOG.debug(f"exception caught: {e}")
        raise e

    except Exception as e:
        LOG.debug(f"exception caught class: {e.__class__}")
        LOG.debug(f"exception caught: {e}")

        if "Error from server (AlreadyExists)" not in str(e):
            raise
        LOG.debug("checking whether this is a duplicate request....")
        if not get_model(model, session):
            raise exceptions.AlreadyExists(TYPE_NAME, model.CfnId)

    progress.status = OperationStatus.SUCCESS
    LOG.debug(f"success {progress.__dict__}")
    return progress


@resource.handler(Action.UPDATE)
def update_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
    )
    LOG.debug(f"Update invoke \n\n{request.__dict__}\n\n{callback_context}")
    # TODO: put code here
    _ = progress
    return read_handler(session, request, callback_context)


@resource.handler(Action.DELETE)
def delete_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState

    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.SUCCESS,
        resourceModel=None,
    )
    LOG.debug(f"Delete invoke \n\n{request.__dict__}\n\n{callback_context}")
    if not model:
        return progress

    if not model.ClusterName:
        raise exceptions.InvalidRequest("ClusterName is required.")

    physical_resource_id, _, manifest_list = handler_init(
        model, session, request.logicalResourceIdentifier, request.clientRequestToken
    )

    kubectl.delete(manifest_list)

    return progress


@resource.handler(Action.READ)
def read_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    LOG.debug(f"Read invoke \n\n{request.__dict__}\n\n{callback_context}")
    # TODO: put code here
    return ProgressEvent(
        status=OperationStatus.SUCCESS,
        resourceModel=model,
    )


@resource.handler(Action.LIST)
def list_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    LOG.debug(f"List invoke \n\n{request.__dict__}\n\n{callback_context}")
    # TODO: put code here
    return ProgressEvent(
        status=OperationStatus.SUCCESS,
        resourceModels=[],
    )
