import sqlite3

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class Project(db.Model):
    __tablename__ = 'projects'
    __table_args__ = (
        db.CheckConstraint('agreed_revisions >= 0', name='ck_projects_agreed_revisions_nonneg'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    client_id = db.Column(
        db.Integer,
        db.ForeignKey('clients.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    agreed_revisions = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(
        db.Enum('Active', 'Completed', 'On-hold', name='project_status_enum'),
        nullable=False,
        default='Active',
    )
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())



class RevisionRequest(db.Model):
    __tablename__ = 'revision_requests'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    description = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum('Pending', 'Completed', 'Rejected', name='revision_status_enum'),
        nullable=False,
        default='Pending',
    )
    is_extra = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    