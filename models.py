from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Day(Base):
    __tablename__ = "days"

    id = Column(Integer, primary_key=True)
    date = Column(String(20))
    title = Column(String(100))
    description = Column(Text, default="")
    spots = relationship(
        "Spot",
        back_populates="day",
        order_by="Spot.order_index",
        cascade="all, delete-orphan",
    )


class Spot(Base):
    __tablename__ = "spots"

    id = Column(Integer, primary_key=True)
    day_id = Column(Integer, ForeignKey("days.id"))
    name = Column(String(100))
    category = Column(String(50))
    time = Column(String(10), default="")
    notes = Column(Text, default="")
    map_url = Column(String(500), default="")
    order_index = Column(Integer, default=0)
    day = relationship("Day", back_populates="spots")
