FROM public.ecr.aws/emr-serverless/spark/emr-7.1.0:latest

USER root

COPY --chown=hadoop:hadoop src/ /app/src/

ENV PYTHONPATH="/app:${PYTHONPATH}"

USER hadoop:hadoop