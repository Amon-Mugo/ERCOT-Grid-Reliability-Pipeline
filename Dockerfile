FROM public.ecr.aws/emr-serverless/spark/emr-7.1.0:latest

USER root

COPY --chown=hadoop:hadoop src/ /app/src/
COPY --chown=hadoop:hadoop src/transform/run_transform.py /usr/lib/spark/work-dir/run_transform.py

ENV PYTHONPATH="/app:${PYTHONPATH}"

USER hadoop:hadoop