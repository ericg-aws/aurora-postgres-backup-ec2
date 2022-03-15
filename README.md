# AWS Aurora Postgres Logical Backup and Restore

## Summary
Solution for automating Logical backups for a specific Aurora PostgreSQL database using pg_dump/pg_restore utilities. The pg_dump utility uses the COPY command to create a schema and data dump of a PostgreSQL database. This is quite useful because it allows a database to be restored to a lower environment. The backup process is done via parallel directory style to decrease the backup time. After a restore is done, a vacuum analyze is done on each table restored. 

The main AWS services used are Ec2, Secrets Manager, Systems Manager, and S3 (with endpoints). This approach was chosen due to a customer's approved service list. A similar apprach was tested on ECS and EKS, with ECS and Ec2 approaches being the lesser complicated approach assuming skills are equal. Backups are stored in S3 with lifecycle rules based on path. The Ec2 instance is postioned in the correct Availability Zone to minimize cross-AZ transfer costs.

## Prerequisites
- Aurora master user credentials stored in Secrets Manager 
- Existing VPC and Subnets setup prior
- RDS security group access given to Ec2 subnet
- S3 KMS encryption key defined 
- Update <region>.vars files in terraform-common and terraform-backup directories
- Update Terraform backend for terraform-common and terraform-backup to use S3 and DynamoDB
- Env variables used by Terraform in the .envrc file

## Main steps 
- Execute main.sh shell script
- Python script, gather-aurora-info.py, gathers information on Aurora setup (to later position the Ec2 in the correct AZ)
- Common regional commponents (that remain long term) are deployed via Terraform
- Temporary Ec2 backup commponents are deployed via Terraform
- Syncing of Ec2 scripts to the S3 Bucket
- Execution of shell script on Ec2 via Systems Manager is done to prepare OS then execute aurora-operation.py that drive the main Aurora backup or restore operation
- The temporary Terraform Ec2 is destroyed (common regional components remain)

## Deployment 

```bash
# backup 
bash main.sh -c <cluster> -d <database> -o backup -r <region> -b <bucket>

bash main.sh -c clu02 -d db3 -o backup -r us-east-2 -b backup-aurora-dev-us-east-2 -s /aurora/clu02/postgres 

# restore
bash main.sh -c <cluster> -d <database> -o restore -r <region> -b <bucket> -s <secret> -t <timestamp>

bash main.sh -c clu02 -d db3 -o restore -r us-east-2 -b backup-aurora-prod-us-east-2 -s /aurora/clu02/postgres -t 20220312T024658Z
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)
