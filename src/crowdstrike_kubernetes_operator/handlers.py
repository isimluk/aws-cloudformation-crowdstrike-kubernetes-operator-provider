import logging
from typing import Any, MutableMapping, Optional
from ruamel import yaml

from cloudformation_cli_python_lib import (
    Action,
    HandlerErrorCode,
    OperationStatus,
    ProgressEvent,
    Resource,
    SessionProxy,
    exceptions,
    identifier_utils,
)

from .models import ResourceHandlerRequest, ResourceModel
from .utils import build_model, encode_id, get_model, handler_init, run_command, stabilize_job
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
    if "stabilizing" in callback_context:
        if manifest_list[0]["apiVersion"].startswith("batch/") and manifest_list[0]["kind"] == 'Job':
            if stabilize_job(
                model.Namespace, callback_context["name"], model.ClusterName, session
            ):
                progress.status = OperationStatus.SUCCESS
            progress.callbackContext = callback_context
            progress.callbackDelaySeconds = 30
            LOG.debug(f"stabilizing: {progress.__dict__}")
            return progress

    try:
        for manifest in manifest_list:
            ret = kubectl.apply(manifest)
            LOG.debug(f"Apply returned: {ret}")

        build_model(list(yaml.safe_load_all(outp)), model)
    except Exception as e:
        if "Error from server (AlreadyExists)" not in str(e):
            raise
        LOG.debug("checking whether this is a duplicate request....")
        if not get_model(model, session):
            raise exceptions.AlreadyExists(TYPE_NAME, model.CfnId)
    if not model.Uid:
        # this is a multi-part resource, still need to work out stabilization for this
        pass
    elif manifest_list[0]["apiVersion"].startswith("batch/") and manifest_list[0]["kind"] == 'Job':
        callback_context["stabilizing"] = model.Uid
        callback_context["name"] = model.Name
        progress.callbackContext = callback_context
        progress.callbackDelaySeconds = 30
        LOG.debug(f"need to stabilize: {progress.__dict__}")
        return progress
    progress.status = OperationStatus.SUCCESS
    LOG.debug(f"success {progress.__dict__}")
    return progress


def delme():
    # TODO: put code here

    # Example:
    try:

        # primary identifier from example
        primary_identifier = None

        # setting up random primary identifier compliant with cfn standard
        if primary_identifier is None:
            primary_identifier = identifier_utils.generate_resource_identifier(
                stack_id_or_name=request.stackId,
                logical_resource_id=request.logicalResourceIdentifier,
                client_request_token=request.clientRequestToken,
                max_length=255
                )

        if isinstance(session, SessionProxy):
            client = session.client("s3")
        # Setting Status to success will signal to cfn that the operation is complete
        progress.status = OperationStatus.SUCCESS
    except TypeError as e:
        # exceptions module lets CloudFormation know the type of failure that occurred
        raise exceptions.InternalFailure(f"was not expecting type {e}")
        # this can also be done by returning a failed progress event
        # return ProgressEvent.failed(HandlerErrorCode.InternalFailure, f"was not expecting type {e}")

    return read_handler(session, request, callback_context)


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

    physical_resource_id, manifest_file, manifest_list = handler_init(
        model, session, request.logicalResourceIdentifier, request.clientRequestToken
    )

    LOG.debug(f"physical_resource_id\n{physical_resource_id}")
    LOG.debug(f"manifest_list\n{manifest_list}")
    # TODO



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
