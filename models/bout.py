from sqlalchemy import Column, Integer, String, Float, Boolean, CheckConstraint, ForeignKey
from sqlalchemy.orm import validates
from models.base import Base


class Bout(Base):
    __tablename__ = 'bouts'

    # Identity
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    weight_division = Column(String(50), nullable=False)
    rounds_scheduled = Column(Integer, nullable=False, default=3)

    # Fighters
    fighter_one = Column(Integer, ForeignKey('fighters.id'), nullable=False)
    fighter_one_age_at_bout = Column(Integer, nullable=True)
    fighter_two = Column(Integer, ForeignKey('fighters.id'), nullable=False)
    fighter_two_age_at_bout = Column(Integer, nullable=True)

    # Result
    winner = Column(String(50), nullable=False)  # 'fighter_one', 'fighter_two', or 'draw'
    method_of_victory = Column(String(40), nullable=False)
    finish = Column(Boolean, default=False)

    # Stats
    finish_rate_at_bout = Column(Float, nullable=False)

    # Database-level constraints
    __table_args__ = (
        # Identity constraints
        CheckConstraint('rounds_scheduled IN (2, 3, 5)', name='check_rounds_valid'),

        # Fighter constraints
        CheckConstraint('fighter_one != fighter_two', name='check_fighters_distinct'),
        CheckConstraint('fighter_one_age_at_bout IS NULL OR fighter_one_age_at_bout >= 16', name='check_fighter_one_age_minimum'),
        CheckConstraint('fighter_two_age_at_bout IS NULL OR fighter_two_age_at_bout >= 16', name='check_fighter_two_age_minimum'),

        # Result constraints
        CheckConstraint("method_of_victory IN ('KO/TKO', 'SUB', 'DEC', 'NC', 'DQ', 'DRAW')", name='check_method_of_victory'),

        # Stats constraints
        CheckConstraint('finish_rate_at_bout >= 0.0 AND finish_rate_at_bout <= 1.0', name='check_finish_rate_range'),
    )

    # Python-level validation — Identity
    @validates('rounds_scheduled')
    def validate_rounds(self, key, value):
        if value not in (2, 3, 5):
            raise ValueError("rounds_scheduled must be 2, 3, or 5")
        return value

    # Python-level validation — Fighters
    @validates('fighter_one_age_at_bout', 'fighter_two_age_at_bout')
    def validate_fighter_age(self, key, value):
        if value is not None and value < 16:
            raise ValueError(f"{key} must be at least 16 OR None if age is unknown")
        return value

    # Python-level validation — Result
    @validates('method_of_victory')
    def validate_method_of_victory(self, key, value):
        normalized = value.upper()
        valid = {'KO/TKO', 'SUB', 'DEC', 'NC', 'DQ', 'DRAW'}
        if normalized not in valid:
            raise ValueError(f"method_of_victory must be one of {sorted(valid)}")
        return normalized

    # Python-level validation — Stats
    @validates('finish_rate_at_bout')
    def validate_finish_rate(self, key, value):
        if value < 0.0 or value > 1.0:
            raise ValueError("finish_rate_at_bout must be between 0.0 and 1.0")
        return value

    def __repr__(self):
        return f"<Bout(id={self.id}, event_id={self.event_id}, method='{self.method_of_victory}')>"