# atlantis-helm-chart

Procore customizations to the upstream Atlantis Helm Chart repo.

# Docker Image
We have our own custom Dockerfile which adds some utilities on top of the upstream Atlantis image.
* The AWS CLI to the Atlantis image.
* The procore_terraform_wrapper.py script from this repo.

The image is built by CI and pushed to quay.io/procoredevops/atlantis-helm-chart/ using `procore-atlantis-vx.x.x-x.x.x` tags.

## Important Note on AWS CLI
The AWS CLI v2 is not currently (5/4/2021) compatible with Alpine based images. V2 requires glibc, and Alpine images do not have it. They use musl instead, and the AWS CLI v2 is not compatible with musl.

There's a workaround in this thread, but it's complicated.
https://github.com/aws/aws-cli/issues/4685

We could also investigate adding a second container to the atlantis pod that has the AWS CLI installed. We'd then just need to add a wrapper inside the atlantis container which redirects calls to `aws` to run in the other container.

# procore_terraform_wrapper

This script wraps calls to Terraform with the following goals:
1. Ensure any sensitive output is masked using `tfmask`, as the output is posted to GitHub by Atlantis.
2. Preserve the return code of `terraform` commands. Piping them to `tfmask` directly caused the loss of the original return code.
3. Reduce the amount of output from `terraform init` and `terraform plan` when the commands run without errors.

The last goal is acheived by:
1. Removing the messages when downloading external modules during `terraform init`
2. Removing the messages for the state refresh during `terraform plan`.

If the terraform commands return any errors or if the regular expressions used for reducing the output do not match, the full-length output will be printed. All output will still go through tfmask, regardless of errors.

## Usage
This script is intended to be used by Atlantis. You can run it locally for testing too.

```
usage: procore_terraform_wrapper.py [-h] --action {init,plan,apply}

Wraps calls to terraform and tfmask. For use with Atlantis.

optional arguments:
  -h, --help            show this help message and exit
  --action {init,plan,apply}
                        The Terraform command to perform.
```

## Running tests
Run the tests after any changes to the python code.

```
pip3 install -f requirements.txt
pytest ./test/ -vvv
```