from datetime import datetime

from sqlalchemy import Column, DateTime, String, Integer, Float, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"


class FitnessFocus(str, enum.Enum):
    STRENGTH = "strength"
    ENDURANCE = "endurance"
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    FLEXIBILITY = "flexibility"
    GENERAL = "general"


class ExperienceLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Equipment(str, enum.Enum):
    HOME = "home"
    GYM = "gym"
    BODYWEIGHT = "bodyweight"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    age = Column(Integer)
    gender = Column(String(20))
    weight_kg = Column(Float)
    height_cm = Column(Float)
    activity_level = Column(Enum(ActivityLevel))
    fitness_focus = Column(Enum(FitnessFocus))
    experience_level = Column(Enum(ExperienceLevel))
    days_per_week = Column(Integer)
    workout_duration_min = Column(Integer)
    equipment = Column(Enum(Equipment))
    injuries_limitations = Column(Text)
    short_term_goals = Column(Text)
    medium_term_goals = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, focus={self.fitness_focus})>"
