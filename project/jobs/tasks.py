# project/users/tasks.py

from celery import shared_task
from .models import TaskModel,JobModel, db


@shared_task(bind=True)
def start_task(self, job_id, task, max_tasks):
    job = JobModel.query.get(job_id)

  
    task_obj = TaskModel(
        task_name=f"Task {task}", status="Started", task_id=self.request.id, job_id=job.id
    )
    db.session.add(task_obj)
    db.session.commit()
    import time

    time.sleep(10)
    
    task_obj.status = "Completed"
    db.session.commit()

    if task==3:
        task_obj.status = "Waiting"
        job.status = "Waiting"
    elif task < max_tasks:
        start_task.delay(job_id,task + 1, max_tasks)
    else:
        job.status = "Completed"
    db.session.commit()
    
    return {"status": f"Task {task}/{max_tasks} completed!"}


