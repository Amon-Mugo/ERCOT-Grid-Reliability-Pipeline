from pyspark.sql import SparkSession

def get_spark_session(app_name:str="ercot-curated-transform")->SparkSession:
    return(
        SparkSession.builder.appName(app_name)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC")
        .config("spark.executor.extraJavaOptions","-Duser.timezone=UTC")
        .config("spark.sql.parquet.datetimeRebaseModeInRead","CORRECTED")
        .config("spark.sql.parquet.datetimeRebaseModeInWrite","CORRECTED")
        .getOrCreate()

    )