#!/usr/bin/env bash
# purpose: control Aurora info gathering and backup

__parse_args() {
    # parsing input arguments
    while getopts ":h:c:d:o:r:b:s:t:" opt; do
        case ${opt} in
            h)
            echo "Example usage:"
            echo "  main.sh -c <cluster> -d <database> -o backup -r <region> -b <bucket>"
            echo "  main.sh -c <cluster> -d <database> -o restore -r <region> -b <bucket> -s <secret> -t <timestamp>"
            exit 0
            ;;
            c) cluster=${OPTARG};;
            d) database=${OPTARG};;
            o) operation=${OPTARG};;
            r) region=${OPTARG};;
            b) bucket=${OPTARG};;
            s) secret=${OPTARG};;
            t) timestamp=${OPTARG};; # e.g. 20220314T024658Z
            \?)
            echo "Invalid Option: -$OPTARG" 1>&2
            exit 1
            ;;
        esac
    done
    shift $((OPTIND -1))

    # put dummy value if none is set 
    timestamp=${timestamp:-'notime'}  
}

__deploy_terraform() {
    echo "Terraform init starting from ${1}"
    terraform -chdir=${1} init -lock="false"; initreturn=$?

    if [ $initreturn -ne 0 ]
    then
        echo "Terraform init exited with error" >&2
        exit 1
    else
        echo "Terraform plan starting from ${1}"
        terraform -chdir=${1} plan -var-file=${region}.tfvars -lock="false"; planreturn=$?
        echo "Terraform plan exit status: $planreturn"
    fi

    if [ $planreturn -ne 0 ]
    then
        echo "Terraform plan exited with error not applying" >&2
        exit 1
    else
        echo "Terraform apply starting from ${1}"
        terraform -chdir=${1} apply -var-file=${region}.tfvars -lock="false" -auto-approve >&1 | ( grep "Apply complete" ); applyreturn=$?
        echo "Terraform plan exit status: $applyreturn"
    fi

    if [ $initreturn -ne 0 ] || [ $planreturn -ne 0 ] || [ $applyreturn -ne 0 ]
    then
        echo "Terraform init, plan, or apply from ${1}, exited with error"
        exit 1
    fi
}

__destroy_terraform() {
    echo "Terraform destroy starting from ${1}"
    terraform -chdir=${1} destroy -var-file=${region}.tfvars -auto-approve; $destroyreturn=$?

    if [ $destroyreturn -ne 0 ]
    then
        echo "Terraform destory of ${1}, exited with error"
        exit 1
    fi
}

__output_regional_variables() {
    echo "Terraform getting output variables from ${1}"
    terraform -chdir=${1} output -json > tmp/terraform-output.json
}

__sync_ec2_scripts() {
    echo "Syncing scripts to bucket ${1}"
    aws s3 sync ec2-scripts/ s3://${bucket}/ec2-scripts
}


#### main control flow ####

# parse arguments
__parse_args "$@"

# gather aurora info
python gather-aurora-info.py -c ${cluster} -o ${operation} -r ${region} 

# apply regional terraform
__deploy_terraform "terraform-common"

# get variable outputs to use in backup terraform step
__output_regional_variables "terraform-common" 

# deploy ec2 backup terraform step
__deploy_terraform "terraform-backup"

# get ec2 id from backup terraform step
ec2_instance_id=$(terraform -chdir=terraform-backup output -raw ec2_instance_id)

# sync scripts to run on ec2
__sync_ec2_scripts ${bucket}

# Sending SSM command to instance and waiting for completion
endpoint=$(cat tmp/db.json | jq '.endpoint')
python3 execute-ssm.py -c $cluster -d $database -o $operation -r $region -b $bucket -s $secret -e $endpoint -i $ec2_instance_id

# destroy backup terraform
__destroy_terraform "terraform-backup"