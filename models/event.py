from sqlalchemy import Column, Integer, String, Date, Time
from models.base import Base


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False, unique=True)
    country = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    date = Column(Date, nullable=False)
    time = Column(Time)

    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}', date='{self.date}')>"
