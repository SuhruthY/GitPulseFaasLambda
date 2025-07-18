import boto3
import json
import time
import os
import zipfile
import subprocess
import shutil
import sys
from botocore.exceptions import ClientError
from dotenv import load_dotenv


def validate_aws_credentials():
    """Validate AWS credentials are properly configured"""
    load_dotenv()

    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("❌ Missing AWS credentials!")
        print("Please set the following environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nYou can set these in a .env file or export them in your shell")
        sys.exit(1)

    print("✅ AWS credentials found")


def create_deployment_package():
    """Create a Lambda deployment package"""
    zip_path = "/tmp/lambda_function.zip"
    package_dir = "/tmp/lambda_package"

    # Clean old package
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    os.makedirs(package_dir)

    # Install dependencies to package directory
    requirements_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'requirements.txt')
    if os.path.exists(requirements_path):
        print("📦 Installing Lambda dependencies...")
        subprocess.check_call([
            sys.executable, '-m', 'pip',
            'install', '-r', requirements_path,
            '--target', package_dir
        ])

    # Copy main script with modified content
    main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src', 'main.py')
    if os.path.exists(main_path):
        with open(main_path, 'r') as f:
            content = f.read()
        # Add AWS Lambda layer for boto3
        modified_content = "import boto3\n" + content
        lambda_file = os.path.join(package_dir, 'lambda_function.py')
        with open(lambda_file, 'w') as f:
            f.write(modified_content)

    print("🗜️ Creating deployment package...")
    shutil.make_archive(zip_path[:-4], 'zip', package_dir)
    
    shutil.rmtree(package_dir)
    return zip_path


def create_lambda_execution_role(role_name="github_events_role"):
    """Create or fetch IAM Role for Lambda"""
    iam = boto3.client("iam")

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }]
    }

    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    }

    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Execution role for GitHub Events Lambda"
        )
        role_arn = response["Role"]["Arn"]
        print(f"✅ Created IAM Role: {role_arn}")

        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}_policy",
            PolicyDocument=json.dumps(policy_document)
        )
        print("🔗 Attached CloudWatch permissions policy")

        time.sleep(10)
        return role_arn

    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"⚠️ Role '{role_name}' already exists.")
            role = iam.get_role(RoleName=role_name)
            return role["Role"]["Arn"]
        else:
            raise


def deploy_lambda(role_arn, function_name="GitHubEventsLogger"):
    """Deploy Lambda function with EventBridge trigger"""
    lambda_client = boto3.client('lambda')
    events_client = boto3.client('events')
    zip_path = create_deployment_package()

    try:
        with open(zip_path, 'rb') as f:
            zip_content = f.read()

        # Create or update Lambda function
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.handle',
                Code={'ZipFile': zip_content},
                Description='GitHub Events Logger Lambda Function',
                Timeout=300,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN', ''),
                        'TZ': 'Asia/Kolkata',
                        'PYTHONIOENCODING': 'UTF-8'
                    }
                }
            )
            function_arn = response['FunctionArn']
            print(f"✅ Created Lambda function: {function_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print(f"⚠️ Updating existing Lambda function...")
                lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_content
                )
                function_arn = lambda_client.get_function(FunctionName=function_name)['Configuration']['FunctionArn']
            else:
                raise

        # Set up EventBridge rule
        rule_name = f"{function_name}-trigger"
        events_client.put_rule(
            Name=rule_name,
            ScheduleExpression='rate(2 minutes)',
            State='ENABLED'
        )

        events_client.put_targets(
            Rule=rule_name,
            Targets=[{
                'Id': '1',
                'Arn': function_arn
            }]
        )

        # Add permission for EventBridge to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId='EventBridgeInvoke',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=f"arn:aws:events:{os.getenv('AWS_DEFAULT_REGION')}:{function_arn.split(':')[4]}:rule/{rule_name}"
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceConflictException':
                raise

        print(f"⏰ Set up EventBridge trigger (every 2 minutes)")
        return function_arn

    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


if __name__ == "__main__":
    validate_aws_credentials()
    role_arn = create_lambda_execution_role()
    lambda_arn = deploy_lambda(role_arn)
    print(f"✨ Deployment complete! Lambda ARN: {lambda_arn}")
    print("📝 Check AWS CloudWatch logs to see the execution logs")
     # Exit immediately to prevent main.py from running
    sys.exit(0)
