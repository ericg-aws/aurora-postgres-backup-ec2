#!/usr/bin/env python 

import argparse
import boto3
import time

def ssm_send_command(args):
    ssm_client = boto3.client('ssm', region_name=args.region) 
    command_string = f'prepare-execute.sh -c {args.cluster} -d {args.database} -o {args.operation} -b {args.bucket} -s {args.secret} -e {args.endpoint} -r {args.region} -t {args.timestamp}'
    s3_path = f'https://{args.bucket}.s3.amazonaws.com/ec2-scripts/prepare-execute.sh'

    print(f'Submitting SSM command: {command_string}')
    try:
        response = ssm_client.send_command(
            InstanceIds=[
                args.instance
            ],
            DocumentName='AWS-RunRemoteScript',
            Parameters={
                'sourceType': ['S3'],
                'sourceInfo':[
                    '{"path": "' + s3_path + '"}'
                ],
                'commandLine':[
                    command_string
                ]
            },
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': '/aws/ssm/aurora-backup',
                'CloudWatchOutputEnabled': True
            }
        )

        command_id = response['Command']['CommandId']
        time.sleep(2)
        output = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=args.instance,
        )
        print(f'SSM command in-progress, ID: {command_id}')
        while output['Status'] != 'Success':
            time.sleep(3)
            output = ssm_client.get_command_invocation(CommandId=command_id, InstanceId=args.instance)
            if (output['Status'] == 'Failed') or (output['Status'] == 'Cancelled') or (output['Status'] == 'TimedOut'):
                print(f'SSM command complete, ID: {command_id}, status of: {output["Status"]}' )
                break

    except Exception as e:
        print(f'Exception during download execution of SSM command {command_string}')
        print(e)

if __name__ == '__main__':

    # python execute-ssm.py 
    # input parsing
    parser = argparse.ArgumentParser(description='aurora ssm prepprogram')
    parser.add_argument('-d', '--database', help='database name', required=True)
    parser.add_argument('-o', '--operation', help='operation type', required=True, choices=['backup', 'restore'])
    parser.add_argument('-b', '--bucket', help='service check', required=True)
    parser.add_argument('-s', '--secret', help='secret', required=True)
    parser.add_argument('-c', '--cluster', help='cluster name', required=True)
    parser.add_argument('-e', '--endpoint', help='instance endpoint', required=True)
    parser.add_argument('-r', '--region', help='aws region for db', required=True, default='us-east-1')
    parser.add_argument('-t', '--timestamp', help='backup timestamp to restore', required=False, default='notime')
    parser.add_argument('-i', '--instance', help='ec2 instance id', required=True)
    args = parser.parse_args()

    # get ssm command id output
    command_id = ssm_send_command(args)
