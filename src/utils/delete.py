import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os
import sys

def delete_cloudwatch_logs(function_name="GitHubEventsLogger"):
    """Delete CloudWatch log groups for Lambda function"""
    logs_client = boto3.client('logs')
    log_group_name = f"/aws/lambda/{function_name}"
    
    try:
        logs_client.delete_log_group(logGroupName=log_group_name)
        print(f"✅ Deleted CloudWatch log group: {log_group_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"ℹ️ Log group '{log_group_name}' does not exist.")
        else:
            raise

def delete_lambda_function(function_name="GitHubEventsLogger"):
    """Delete Lambda function if it exists"""
    lambda_client = boto3.client('lambda')
    
    try:
        lambda_client.delete_function(FunctionName=function_name)
        print(f"✅ Deleted Lambda function: {function_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"ℹ️ Lambda function '{function_name}' does not exist.")
        else:
            raise

def delete_iam_role(role_name="github_events_role"):
    """Delete IAM role and its policies"""
    iam = boto3.client('iam')
    
    try:
        # Delete inline policies
        try:
            policies = iam.list_role_policies(RoleName=role_name)
            for policy_name in policies.get('PolicyNames', []):
                iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
                print(f"✅ Deleted inline policy: {policy_name}")
        except ClientError:
            pass

        # Detach and delete managed policies
        try:
            attached_policies = iam.list_attached_role_policies(RoleName=role_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                iam.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
                print(f"✅ Detached managed policy: {policy['PolicyName']}")
        except ClientError:
            pass

        # Delete the role
        iam.delete_role(RoleName=role_name)
        print(f"✅ Deleted IAM role: {role_name}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"ℹ️ IAM role '{role_name}' does not exist.")
        else:
            raise

def delete_eventbridge_rule(function_name="GitHubEventsLogger"):
    """Delete EventBridge rule and targets"""
    events_client = boto3.client('events')
    rule_name = f"{function_name}-trigger"
    
    try:
        # Remove targets first
        events_client.remove_targets(
            Rule=rule_name,
            Ids=['1']
        )
        print(f"✅ Removed EventBridge targets for rule: {rule_name}")
        
        # Delete the rule
        events_client.delete_rule(
            Name=rule_name
        )
        print(f"✅ Deleted EventBridge rule: {rule_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"ℹ️ EventBridge rule '{rule_name}' does not exist.")
        else:
            raise

if __name__ == "__main__":
    load_dotenv()
    print("🧹 Starting cleanup...")
    # Order matters: remove triggers first, then function, then role
    delete_eventbridge_rule()
    delete_lambda_function()
    delete_cloudwatch_logs()
    delete_iam_role()
    print("✨ Cleanup complete!")
    # Exit immediately to prevent main.py from running
    sys.exit(0)
