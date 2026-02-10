from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(200))
    subject = Column(String(100))
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
