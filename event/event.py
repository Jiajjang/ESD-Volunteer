# where the Event entity is (like the database structure)

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Event(db.Model):
    __tablename__ = 'event'

    event_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    organiser_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE')
    max_capacity = db.Column(db.Integer, nullable=False)
    current_capacity = db.Column(db.Integer, default=0)
    location = db.Column(db.Text)
    reason = db.Column(db.Text)

    def json(self):
        return {
            "eventID": self.event_id,
            "name": self.name,
            "description": self.description,
            "startDate": self.start_date.isoformat() if self.start_date else None,
            "endDate": self.end_date.isoformat() if self.end_date else None,
            "organiserID": self.organiser_id,
            "status": self.status,
            "maxCapacity": self.max_capacity,
            "currentCapacity": self.current_capacity,
            "location": self.location,
            "reason": self.reason
        }
    

    