#used in error handling and alerts to user email rather than slack

import logging
import smtplib
from email.mime.text import MIMEText
from airflow.models import Variable

logger=logging.getLogger("airflow.task")

def task_failure_alert(context:dict) -> None:

    try:
        task_instance=context["task_instance"] # get task instance (python object)
        dag=context.get("dag")  # get dag (python object)
        dag_id=dag.dag_id if dag else "Unknown_dag" #get dag name
        task_id=task_instance.task_id #gets task name
        execution_date=context.get("logical_date") or context.get("execution_date") #get execution date
        log_url=getattr(task_instance,"log_url","N/A") #get log url
        exception=context.get("exception","No exception details provided") # holds error message
        subject=f"[Airflow_Failure] {dag_id}.{task_id}"
        body=(
            f"DAG:{dag_id}\n"
            f"Task:{task_id}\n"
            f"Execution Date:{execution_date}\n"
            f"Exception:{exception}\n"
            f"Log URL:{log_url}\n"

        )

        gmail_user=Variable.get("ercot_alert_gmail_user")
        gmail_app_password=Variable.get("ercot_alert_gmail_app_password")
        recipient_str=Variable.get("ercot_alert_recipient")
        recipients=[r.strip() for r in recipient_str.split(",") if r.strip()]

        msg=MIMEText(body)
        msg["Subject"]=subject
        msg["From"]=gmail_user
        msg["To"]=recipient_str

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls() # secure connection
            server.login(gmail_user,gmail_app_password) # login with gmail_user and gmail_app_password
            server.sendmail(gmail_user,recipients,msg.as_string()) # send email from gmail_user to recipients
            
        logger.info(f"Failure alert email sent successfully for {dag_id}.{task_id}")

    except Exception as e:
        logger.error(f"Failed to send failure alert email via SMTP: {e}",exc_info=True)