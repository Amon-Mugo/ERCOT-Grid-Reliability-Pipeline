from typing import  Generator
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session") # tells spark to run  once per tsest

def spark() -> Generator[SparkSession, None, None]:

    session=(SparkSession.builder.appName("ercot-curated-transform-test")
            .master("local[2]") 
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.driver.extraJavaOptions","-Duser.timezone=UTC")
            .config("spark.sql.parquet.datetimeRebaseModeInRead","CORRECTED")
            .config("spark.sql.parquet.datetimeRebaseModeInWrite","CORRECTED")
            .config("spark.sql.shuffle.partitions","2")
            .config("spark.ui.enabled","false")
            .getOrCreate())
    yield session
    session.stop()

@pytest.fixture(autouse=True) 
def clean_spark_catalog(spark: SparkSession) -> Generator[None, None, None]:
    yield
    spark.catalog.clearCache()
    for table in spark.catalog.listTables():
        if table.isTemporary:
            spark.catalog.dropTempView(table.name)
