#!/usr/bin/env bash
# purpose: control Aurora info gathering and backup

__parse_args() {
    # parsing input arguments
    while getopts ":h:c:d:o:r:b:s:e:t:" opt; do
        case ${opt} in
            h)
            echo "Example usage:"
            echo "  ec2-execute.sh -c clu02 -d db3 -o backup -r us-west-1 -b backup-aurora-prod-us-west-1-01 \
                -s /aurora/clu02/postgres -e clu02.cluster-cryeui-ro.us-west-1.rds.amazonaws.com"
            echo "  ec2-execute.sh -c clu02 -d db3 -o restore -r us-west-1 -b backup-aurora-prod-us-west-1-01 \
                -s /aurora/clu02/postgres -e clu02.cluster-cryeui.us-west-1.rds.amazonaws.com -t 20220312T201225Z"
            exit 0
            ;;
            c) cluster=${OPTARG};;
            d) database=${OPTARG};;
            o) operation=${OPTARG};;
            r) region=${OPTARG};;
            b) bucket=${OPTARG};;
            s) secret=${OPTARG};;
            e) endpoint=${OPTARG};;
            t) timestamp=${OPTARG};;
            \?)
            echo "Invalid Option: -$OPTARG" 1>&2
            exit 1
            ;;
        esac
    done
    shift $((OPTIND -1))
}

__prepare_env() {

    echo "Updating OS packages and getting latest Postgres 13 client package"
    yum -y update 
    yum -y install which amazon-linux-extras wget shadow-utils awscli unzip
    amazon-linux-extras disable postgresql9.6 2>&1
    amazon-linux-extras enable postgresql13 2>&1
    yum -y install postgresql
    yum -y clean all

    if ! command -v /usr/local/bin/aws
    then
        echo "Installing aws cli v2"
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" 
        unzip awscliv2.zip && ./aws/install && rm -rf awscliv2.zip ./aws 2>&1
    fi

    python3 -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    'psycopg2-binary==2.9.*' 2>&1
    python3 -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    'boto3>=1.*' 2>&1
}

__aurora_operation() {
    aws s3 sync s3://${bucket}/ec2-scripts/ .
    
    # put dummy value if none is set 
    timestamp=${timestamp:-'notime'}   
    python3 aurora-operation.py -c ${cluster} -d ${database} -o ${operation} -r ${region} -b ${bucket} -s ${secret} -e ${endpoint} -t ${timestamp}
}

#### main control flow ####

# parse arguments
__parse_args "$@"

# prepare linux env with OS packages updates, postgres client, and python packages
__prepare_env

# download scripts from bucket and run main aurora operation script
__aurora_operation
