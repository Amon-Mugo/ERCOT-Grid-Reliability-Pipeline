# the daily orchestration of the pipeline and runs aon a schedule automatically in airflow

from datetime import datetime,timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator # to execute the python script

from airflow.providers.amazon.aws.operators.emr import EmrServerlessStartJobOperator # used to import to launch and monitor jobs in AWS EMR

from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from utils.callbacks import task_failure_alert # used to import a python function from callbacks.py

DEFAULT_ARGS={
    "owner":"amon",
    "retries":1,
    "retry_delay":timedelta(minutes=5),
    "on_failure_callback":task_failure_alert, #imports finction fror error handling
}

AWS_CONN_ID="aws_default"  # the connection id for the AWS connection

SNOWFLAKE_CONN_ID="snowflake_default"  # the connection id for the snowflake connection

def run_ingestion(**_context) -> None:
    from ingestion.ingest import run_ingestion as ingest_main # import the main function from ingest.py

    ingest_main() # run the ingestion to ingest data from the EIA API and s3 loader for orchestration


#DAG definition
with DAG(
    dag_id="ercot_pipeline",
    description="EIA ingestion -> EMR Serverless transform -> Snowflake load",
    default_args=DEFAULT_ARGS,
    schedule="0 6 * * *", # runs everyday at 6am rather than daily many ingest conlicting data
    start_date=datetime(2026,8,1),
    catchup=False,
    tags=["ercot"],

) as dag:
    #define airflow tasks to execute python scripts
    ingest=PythonOperator(
        task_id="ingest_eia_to_s3",
        python_callable=run_ingestion,
    )

    #  Airflow templates Variable access at execution time rather than DAG parse time
    #emr severless transform
    transform=EmrServerlessStartJobOperator(
        task_id="transform_curated_spark",
        aws_conn_id=AWS_CONN_ID,
        application_id="{{ var.value.ercot_emr_application_id }}",
        execution_role_arn="{{ var.value.ercot_emr_execution_role_arn }}",
        job_driver={
            "sparkSubmit":{
                "entryPoint":"local:///usr/lib/spark/work-dir/run_transform.py",# the entry point for the spark job
                "entryPointArguments":[],
                "sparkSubmitParameters":(
                    f"--py-files {{{{ var.value.ercot_src_package_s3_path }}}} "
                    "--conf spark.executor.cores=1 "
                    "--conf spark.executor.memory=4g "
                    "--conf spark.driver.cores=1 "
                    "--conf spark.driver.memory=4g"
                                        
                ),

                
            }
        },

        #emr serverless cluster configuration
        configuration_overrides={
            "monitoringConfiguration":{
                "s3MonitoringConfiguration":{
                    "logUri":"s3://{{ var.value.ercot_curated_bucket }}/emr-logs/",
                }
            }
        },

        wait_for_completion=True,
        name="ercot-transform-{{ ds }}",
    )

    #snowflake load,queries and operations 
    load = SQLExecuteQueryOperator(
    task_id="load_raw_snowflake",
    conn_id=SNOWFLAKE_CONN_ID,
    sql=[
        "CALL load_raw_demand('{{ ds }}');",
        "CALL load_raw_interchange('{{ ds }}');",
        "CALL load_raw_generation_by_fuel('{{ ds }}');",
    ],
    hook_params={
        "role": "ERCOT_LOADER",
        "warehouse": "COMPUTE_WH",
        "database": "AWS_SNOWFLAKE_PIPELINE",
        "schema": "RAW",
    },
)
    ingest >> transform >> load

