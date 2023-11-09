from flask import Blueprint,jsonify,request
from sqlalchemy import desc,delete
from project import ext_celery


jobs_blueprint = Blueprint("jobs", __name__, url_prefix="/jobs", template_folder="templates")

from . import models, tasks


@jobs_blueprint.route("", methods=["POST"])
def start_job():
    job_title = request.json.get('jobTitle',"Job")
    

    job_obj = models.JobModel(
        job_name=job_title, status="Started"
    )
    models.db.session.add(job_obj)
    models.db.session.commit()
    
    task = tasks.start_task.delay(job_obj.id,1, 5)  # Call the task with delay
    return jsonify({"task_id": task.id}), 202

@jobs_blueprint.route("", methods=["GET"])
def get_jobs():

    jobs = models.db.session.query(models.JobModel).order_by(desc(models.JobModel.created)).all()
    job_list = []
    for job in jobs:
        jobs = models.db.session.query(models.JobModel).all()
        job_data = {
            'id': job.id,
            'job_name': job.job_name,
            'status': job.status,
             'created': job.created,
            'tasks':[]
        }
        for task in models.TaskModel.query.filter_by(job_id=job.id).order_by(models.TaskModel.id):
            task_data = {
                'task_name': task.task_name,
                'task_id': task.task_id,
                'status': task.status,
                'created': task.created,
                 'updated': task.updated,
            }
            job_data['tasks'].append(task_data)
        job_list.append(job_data)
    return jsonify({"jobs": job_list}), 202

@jobs_blueprint.route("", methods=["DELETE"])
def clear_jobs():

    with models.db.session.begin():
        tasks_list = models.db.session.query(models.TaskModel).filter(models.TaskModel.status == "Started").all()

        for task in tasks_list:
            ext_celery.celery.control.revoke(task.task_id, terminate=True)

        # Delete all tasks. This deletes all rows from the TaskModel table.
        models.db.session.execute(delete(models.TaskModel))

        # Delete all jobs. This deletes all rows from the JobModel table.
        models.db.session.execute(delete(models.JobModel))

    # Commit the transaction
    models.db.session.commit()
    
    return jsonify({"message": "success"}), 200

@jobs_blueprint.route("<id>/cancel", methods=["GET"])
def cancel_job(id):

    job = models.JobModel.query.get(id)
    tasks_list = models.db.session.query(models.TaskModel).filter(models.TaskModel.job_id==id).filter(models.TaskModel.status != "Completed").all()

    for task in tasks_list:
            
            ext_celery.celery.control.revoke(task.task_id, terminate=True)
            task.status="Canceled"
            models.db.session.commit()

    job.status="Canceled"
    models.db.session.commit()
    
    return jsonify({"message": "success"}), 200

@jobs_blueprint.route("task/<id>/resume", methods=["GET"])
def resume_job(id):

    task = models.TaskModel.query.filter_by(task_id=id).first()

    job = task.job
         
    task.status="Completed"
            

    job.status="Started"
    models.db.session.commit()

    task = tasks.start_task.delay(job.id,4, 5)  # Call the task with delay
    
    return jsonify({"message": "success"}), 200