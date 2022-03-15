import argparse 
import boto3
from boto3.s3.transfer import TransferConfig
import base64
from botocore.exceptions import ClientError
import datetime
import json
import os
import pathlib
import psycopg2
import shutil
import subprocess
import sys

def get_nested(data, *args):
    if args and data:
        element  = args[0]
        if element:
            value = data.get(element)
            return value if len(args) == 1 else get_nested(value, *args[1:])

def get_date():
    current_date = datetime.datetime.utcnow().strftime("%Y%m%d")
    return current_date

def get_time():
    current_time = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return current_time

def get_secret(secret_name, region):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return json.loads(secret) 
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return decoded_binary_secret

def perform_db_backup(instance_username, instance_password, instance_port, env_path, current_time, args):
    print(f'Backing up {args.database} database from cluster {args.endpoint}')

    command1 =  f'PATH={env_path} ' \
                f'pg_dump -Fd '\
                f'--host={args.endpoint} ' \
                f'--username={instance_username} ' \
                f'--no-password ' \
                f'--port={instance_port} ' \
                f'-Z 1 ' \
                f'-j 8 ' \
                f'-f /tmp/{args.cluster}-{args.database}-{current_time} ' \
                f'{args.database}'

    try:
        bufsize = 1024 * 1024 * 1 # 1MB

        proc1 = subprocess.Popen(command1, shell=True, stdin=subprocess.PIPE, \
            stdout=subprocess.PIPE, bufsize=bufsize, env={
            'PGPASSWORD': instance_password
            })
        out, err = proc1.communicate()
        if proc1.returncode != 0:
            return None

    except Exception as e:
            print(f'Exception during dump of {args.database} database from cluster {args.endpoint}')
            print(e)

def perform_db_restore(backup_type, instance_username, instance_password, instance_port, env_path, args):
    print(f'Restoring {args.database} database to cluster {args.endpoint} on port {instance_port}')
    # pg_restore -U postgres -Ft -C -d db1
    # pg_restore --dbname=DBNAME --no-tablespaces --host=HOSTNAME --port=5432 --username=USERNAME --verbose -F d -j 6 /mnt/backup
    command1 =  f'PATH={env_path} ' \
                f'pg_restore -C ' \
                f'--host={args.endpoint} ' \
                f'--username={instance_username} ' \
                f'--no-password ' \
                f'--port={instance_port} ' \
                f'-v ' \
                f'-d postgres ' \
                f'/tmp/{args.cluster}-{args.database}-{args.timestamp} ' 

    try:
        bufsize = 1024 * 1024 * 1 # 1MB

        proc1 = subprocess.Popen(command1, shell=True, stdin=subprocess.PIPE, \
            stdout=subprocess.PIPE, bufsize=bufsize, env={
            'PGPASSWORD': instance_password
            })
        out, err = proc1.communicate()
        if proc1.returncode != 0:
            return None

    except Exception as e:
            print(f'Exception during restore of {args.database} database to cluster {args.endpoint}')
            print(e)

def check_existing_db(instance_username, instance_password, instance_port, env_path, args):
    print(f'Checking if database, {args.database} exists on cluster {args.endpoint} on port {instance_port}')
    connection = None
    db_found = False
    try:
        conn_string = f'user={instance_username} password={instance_password} host={args.endpoint} port={instance_port}'
        connection = psycopg2.connect(conn_string)
        print('Connected to database')
    except Exception as e:
        print('Unable to connect to database')
        print(e)
    try:
        if connection is not None:
            connection.autocommit = True
            cur = connection.cursor()
            cur.execute("SELECT datname FROM pg_database;")
            db_list = cur.fetchall()

            for db in db_list:
                if (db[0]) == args.database:
                    print(f'Database {db[0]} exists')
                    db_found = True 
        cur.close()
        connection.close()
    except Exception as e:
            print(f'Exception during check if database {args.database} exists on cluster {args.endpoint}')
            print(e)
    return db_found

def drop_tables(instance_username, instance_password, instance_port, env_path, args):
    print(f'Drop tables on database, {args.database}, on cluster {args.endpoint} on port {instance_port}')
    connection = None
    db_found = False
    try:
        conn_string = f'user={instance_username} password={instance_password} host={args.endpoint} port={instance_port} dbname={args.database}'
        connection = psycopg2.connect(conn_string)
        print('Connected to database')
    except Exception as e:
        print('Unable to connect to database')
        print(e)
    try:
        if connection is not None:
            connection.autocommit = True
            cur = connection.cursor()
            cur.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_schema,table_name")
            cur_result = cur.fetchall()
            print(cur_result)
            for row in cur_result:
                print(f'Dropping tables: {row[1]}')
                cur.execute("drop table " + row[1] + " cascade")
        cur.close()
        connection.close()
    except Exception as e:
            print(f'Exception during dropping tables on database {args.database} on cluster {args.endpoint}')
            print(e)
    return db_found

def vacuum_analyze_tables(instance_username, instance_password, instance_port, env_path, args):
    print(f'Vacuum and analyze for tables on database, {args.database}, on cluster {args.endpoint} on port {instance_port}')
    connection = None
    db_found = False
    try:
        conn_string = f'user={instance_username} password={instance_password} host={args.endpoint} port={instance_port} dbname={args.database}'
        connection = psycopg2.connect(conn_string)
        print('Connected to database')
    except Exception as e:
        print('Unable to connect to database')
        print(e)
    try:
        if connection is not None:
            connection.autocommit = True
            print("hi")
            cur = connection.cursor()
            cur.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_schema,table_name")
            cur_result = cur.fetchall()
            print(cur_result)
            for row in cur_result:
                print(f'Vacuum and analyze table: {row[1]}')
                cur.execute("VACUUM(FULL, ANALYZE, VERBOSE) " + row[1])
        cur.close()
        connection.close()
    except Exception as e:
            print(f'Exception during vacuum and analyze tables on database {args.database} on cluster {args.endpoint}')
            print(e)
    return db_found

def perform_roles_backup(backup_type, instance_username, instance_password, instance_port, env_path, current_time, args):
    print(f'Backing up roles from cluster {args.endpoint}')

    s3_file = f'{backup_type}/{args.cluster}/roles/{current_time}/roles.dump'

    command1 =  f'PATH={env_path} ' \
                f'pg_dumpall --host={args.endpoint} ' \
                f'--username={instance_username} ' \
                f'--no-password ' \
                f'--port={instance_port} ' \
                f'--no-role-passwords --roles-only ' 
    
    command2 =  f'PATH={env_path} ' \
                f'aws s3 cp - --region={args.region} ' \
                f's3://{args.bucket}/{s3_file}' 

    try:
        bufsize = 1024 * 1024 * 1 # 1MB

        proc1 = subprocess.Popen(command1, shell=True, stdin=subprocess.PIPE, \
            stdout=subprocess.PIPE, bufsize=bufsize, env={
            'PGPASSWORD': instance_password
            })

        proc2 = subprocess.Popen(command2, shell=True, stdin=proc1.stdout, stdout=subprocess.PIPE)
        proc2.wait()
    except Exception as e:
        print(f'Exception during dump of roles data from cluster {args.endpoint}')
        print(e)

def copy_to_s3(backup_type, current_time, args):
    s3_resource = boto3.resource('s3', region_name=args.region)
    # get file list
    input_path = f'/tmp/{args.cluster}-{args.database}-{current_time}'

    for filepath in pathlib.Path(input_path).glob('**/*'):
        full_path = str(filepath.absolute())
        file_name = str(filepath.name)
        s3_key_name = f'{backup_type}/{args.cluster}/{args.database}/{current_time}/{file_name}'
        try:
            config = TransferConfig(multipart_threshold=1024 * 25, 
                        max_concurrency=8,
                        multipart_chunksize=1024 * 25,
                        use_threads=True)

            s3_resource.Object(args.bucket, s3_key_name).upload_file(full_path,
                ExtraArgs={'ContentType': 'application/x-compressed'},
                Config=config
                )
        except Exception as e:
            print(f'Exception during copy of {s3_key_name} to {args.bucket}')
            print(e)
    # clean up files once copied 
    shutil.rmtree(input_path)

def copy_from_s3(backup_type, args):
    s3_resource = boto3.resource('s3', region_name=args.region)
    bucket = s3_resource.Bucket(args.bucket)
    # get file list
    s3_prefix = f'{backup_type}/{args.cluster}/{args.database}/{args.timestamp}'
    download_dir = f'/tmp/{args.cluster}-{args.database}-{args.timestamp}'
    pathlib.Path(download_dir).mkdir(parents=True, exist_ok=True)

    print(f'Downloading from s3 prefix of {s3_prefix}')
    prefix_objs = bucket.objects.filter(Prefix=s3_prefix)
    for obj in prefix_objs:
        try:
            s3_key_name = obj.key
            s3_file_name = s3_key_name.rsplit('/', 1)[-1]
            download_full_path = f'{download_dir}/{s3_file_name}'
            config = TransferConfig(multipart_threshold=1024 * 25, 
                        max_concurrency=8,
                        multipart_chunksize=1024 * 25,
                        use_threads=True)

            s3_resource.Object(args.bucket, s3_key_name).download_file(download_full_path,
                        Config=config
            )
        except Exception as e:
            print(f'Exception during download of {s3_key_name} to {args.bucket}')
            print(e)

def main():

    # python aurora_operation.py -c clu02 -d db3 -o backup -r us-east-1 -b backup-aurora-prod-us-east-1 -s /aurora/clu02/postgres -e clu02.cluster-ro-crywpxf9avmu.us-east-1.rds.amazonaws.com
    # input parsing
    parser = argparse.ArgumentParser(description='aurora operation program')
    parser.add_argument('-d', '--database', help='database name', required=True)
    parser.add_argument('-o', '--operation', help='operation type', required=True, choices=['backup', 'restore'])
    parser.add_argument('-b', '--bucket', help='service check', required=True, default=False)
    parser.add_argument('-s', '--secret', help='secret', required=True)
    parser.add_argument('-c', '--cluster', help='cluster name', required=True)
    parser.add_argument('-e', '--endpoint', help='instance endpoint', required=True)
    parser.add_argument('-r', '--region', help='aws region for db', required=True, default='us-east-1')
    parser.add_argument('-t', '--timestamp', help='backup timestamp to restore', required=False)
    args = parser.parse_args()

    # required env variables 
    env_path = os.getenv('PATH', '/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin')
    user_home = os.getenv('HOME')

    # gather secret and associated details - required for script
    secret_dict = get_secret(args.secret, args.region)
    instance_username = get_nested(secret_dict, 'username')
    instance_password = get_nested(secret_dict, 'password')
    instance_port =  get_nested(secret_dict, 'port')

    current_time = get_time()
    current_date = get_date()

    # if no specific database is specified - backup all databases
    if (args.database) and (args.operation == 'backup'):
        print(f'Backing up single database of: {args.database}, on host: {args.endpoint}')
        backup_type = 'manual'
        perform_db_backup(instance_username, instance_password, instance_port, \
            env_path, current_time, args)
        perform_roles_backup(backup_type, instance_username, instance_password, instance_port, \
            env_path, current_time, args)
        copy_to_s3(backup_type, current_time, args)
    elif (args.database) and (args.operation == 'restore') and (args.timestamp):
        backup_type = 'manual'
        db_found = check_existing_db(instance_username, instance_password, instance_port, env_path, args)
        if db_found == True:
            drop_tables(instance_username, instance_password, instance_port, env_path, args)
        print(f'Restoring single database of: {args.database}, on host: {args.endpoint}, backup timestamp of: {args.timestamp} ')
        copy_from_s3(backup_type, args)
        perform_db_restore(backup_type, instance_username, instance_password, instance_port, env_path, args)
        vacuum_analyze_tables(instance_username, instance_password, instance_port, env_path, args)
    else:
        print('No known operation matched')
    
    print(f'{args.operation} for instance {args.cluster} operation complete')

if __name__ == "__main__":
    main()
