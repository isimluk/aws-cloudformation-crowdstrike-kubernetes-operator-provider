# CrowdStrike::Kubernetes::Operator

An example resource schema demonstrating some basic constructs and validation rules.

## Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON

<pre>
{
    "Type" : "CrowdStrike::Kubernetes::Operator",
    "Properties" : {
        "<a href="#clustername" title="ClusterName">ClusterName</a>" : <i>String</i>
    }
}
</pre>

### YAML

<pre>
Type: CrowdStrike::Kubernetes::Operator
Properties:
    <a href="#clustername" title="ClusterName">ClusterName</a>: <i>String</i>
</pre>

## Properties

#### ClusterName

Name of the EKS cluster

_Required_: Yes

_Type_: String

_Update requires_: [Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)

## Return Values

### Ref

When you pass the logical ID of this resource to the intrinsic `Ref` function, Ref returns the ClusterName.
