#!/usr/bin/env python 

import argparse
import boto3
import json
import os

def get_instance_info(client, db_id):
    response = client.describe_db_instances(
        DBInstanceIdentifier=db_id,
    )

    az = response['DBInstances'][0]['AvailabilityZone']
    subnets = response['DBInstances'][0]['DBSubnetGroup']['Subnets']
    for subnet in subnets:
        if az in str(subnet):
            subnet_id = subnet['SubnetIdentifier']
    return az, subnet_id

def get_cluster_info(args):
    client = boto3.client('rds', region_name=args.region)
    response = client.describe_db_clusters(
        DBClusterIdentifier=args.cluster
    )

    port = response['DBClusters'][0]['Port']
    members = response['DBClusters'][0]['DBClusterMembers']

    if args.operation == 'backup':
        endpoint = response['DBClusters'][0]['ReaderEndpoint']
        for member in members:
            if member['IsClusterWriter'] == False:
                db_id = member['DBInstanceIdentifier']
                az, subnet_id = get_instance_info(client, db_id)
                print(f'Found reader endpoint of: {endpoint}, instance: {db_id}, in az: {az}')
    else:
        endpoint = response['DBClusters'][0]['Endpoint']
        for member in members:
            if member['IsClusterWriter'] == True:
                db_id = member['DBInstanceIdentifier']
                az, subnet_id = get_instance_info(client, db_id)
                print(f'Found writer endpoint of: {endpoint}, instance: {db_id}, in az: {az}')
    return endpoint, az, subnet_id


if __name__ == '__main__':

    # example input
    # python gather-aurora-info.py -c clu02 -o backup -r us-east-1
    # input parsing
    parser = argparse.ArgumentParser(description='data prep program')
    parser.add_argument('-c', '--cluster', help='cluster name', required=True)
    parser.add_argument('-o', '--operation', help='operation type', required=True, choices=['backup', 'restore'])
    parser.add_argument('-r', '--region', help='aws region for db', required=True, default='us-east-1')
    args = parser.parse_args()

    # get reader or writer endpoint based upon operation being backup or restore
    endpoint, az, subnet_id = get_cluster_info(args)
    
    # wrote json output to be consumed by backup terrraform step 
    db_dict = {'az': az, 'endpoint': endpoint, 'subnet_id': subnet_id}
    
    with open('tmp/db.json', 'w') as json_file:
        json.dump(db_dict, json_file)