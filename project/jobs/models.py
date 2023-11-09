from project import db
from sqlalchemy.sql import func

class JobModel(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(20))
    status = db.Column(db.String(20))

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    tasks = db.relationship('TaskModel', backref='job', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_name": self.job_name,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
        }


class TaskModel(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Text())
    task_name = db.Column(db.String(20))
    status = db.Column(db.String(20))

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'),
        nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
        }