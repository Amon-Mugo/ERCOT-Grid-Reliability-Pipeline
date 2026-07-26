import logging
from datetime import datetime,timedelta,timezone
from eia_client import EIAClientError, fetch_dataset
from s3_loader import S3LoaderError,upload_ndjson
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s') #
logger = logging.getLogger(__name__) #trace_logger
RESPONDENT="ERCO"
DATASET={
    "demand":{
        "route":"electricity/rto/region-data/data",
        "facets":{"respondent":[RESPONDENT],"type":["D"]},

    },
    "interchange":{
        "route":"electricity/rto/region-data/data",
        "facets":{"respondent":[RESPONDENT],"type":["TI"]},
    },
    "generation_by_fuel":{
        "route":"electricity/rto/region-data/data",
        "facets":{"respondent":[RESPONDENT]},
    },

}

def get_yesterday_window()->tuple[str,str,str]:

    yesterday=datetime.now(timezone.utc) - timedelta(days=1)
    date_str=yesterday.strftime("%Y-%m-%d")#get yesterday's date
    start=f"{date_str}T00"
    end=f"{date_str}T23"
    return date_str,start,end


# main function

def run_ingestion() -> None:
    date_str,start,end=get_yesterday_window() #get yesterday's date
    logger.info("start ingestion for %s(window %s to %s)",date_str,start,end)
    failures:list[str]=[]
    for dataset_name,config in DATASET.items():

        try:
            row=fetch_dataset(#fetch the data of yesterday
                route=config["route"],
                facets=config["facets"],
                start=start,
                end=end,
            )
            key=upload_ndjson(dataset_name,date_str,row) # enable to upload the data
            logger.info("Uploaded %s to s3://ercot-grid-pipeline-raw/%s", dataset_name, key)

        except (EIAClientError,S3LoaderError) as exc:
            logger.error("failed to fetch datasetname'%s' due to %s",dataset_name,exc)
            failures.append(dataset_name)

    if failures:
        raise RuntimeError(f"failed to ingest dataset: {','.join(failures)}")

    logger.info("ingestion completed for %s",date_str)

if __name__ == "__main__":
    run_ingestion()