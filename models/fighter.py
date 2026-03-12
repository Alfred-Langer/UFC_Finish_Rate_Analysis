from datetime import date
from sqlalchemy import Column, Integer, String, Float, Date, Boolean, CheckConstraint, case
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates
from models.base import Base


class Fighter(Base):
    __tablename__ = 'fighters'

    # Identity
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    nick_name = Column(String(100), nullable=True)
    former_nick_names = Column(String(500), nullable=True)  # Comma-separated list of former nicknames
    sex = Column(String(2), nullable=False, default="M")
    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)  # May not always have the fighter's age

    # Record
    wins = Column(Integer, nullable=False)
    losses = Column(Integer, nullable=False)
    draws = Column(Integer, nullable=False, default=0)
    no_contests = Column(Integer, nullable=False)
    number_of_total_bouts = Column(Integer, nullable=False)
    latest_bout_date = Column(Date, nullable=True)

    # Stats
    overall_finish_rate = Column(Float, nullable=False)

    # Database-level constraints
    __table_args__ = (
        # Identity constraints
        CheckConstraint("sex IN ('M', 'F', 'NA')", name='check_sex_valid'),
        CheckConstraint("date_of_birth IS NULL OR date_of_birth >= '1900-01-01'", name='check_dob_lower_bound'),
        CheckConstraint('age IS NULL OR age >= 16', name='check_age_minimum'),

        # Record constraints
        CheckConstraint('wins >= 0', name='check_wins_non_negative'),
        CheckConstraint('losses >= 0', name='check_losses_non_negative'),
        CheckConstraint('draws >= 0', name='check_draws_non_negative'),
        CheckConstraint('no_contests >= 0', name='check_no_contests_non_negative'),
        CheckConstraint('number_of_total_bouts >= 0', name='check_total_bouts_non_negative'),

        # Stats constraints
        CheckConstraint('overall_finish_rate >= 0.0 AND overall_finish_rate <= 1.0', name='check_overall_finish_rate_range'),
    )

    # Computed property — active_fighter
    @hybrid_property
    def active_fighter(self): # type: ignore
        """True if the fighter has had a bout within the last 10 years, or if no bout date is recorded."""
        if self.latest_bout_date is None:
            return True
        ten_years_ago = date.today().replace(year=date.today().year - 10)
        return self.latest_bout_date >= ten_years_ago

    @active_fighter.expression
    def active_fighter(cls):
        ten_years_ago = date.today().replace(year=date.today().year - 10)
        return case(
            (cls.latest_bout_date == None, True),
            (cls.latest_bout_date >= ten_years_ago, True),
            else_=False,
        )

    # Python-level validation — Identity
    @validates('name')
    def validate_name(self, key, value):
        stripped = value.strip()
        if not stripped:
            raise ValueError("name cannot be empty")
        return stripped

    @validates('sex')
    def validate_sex(self, key, value):
        normalized = value.upper()
        if normalized not in ('M', 'F', 'NA'):
            raise ValueError("sex must be 'M', 'F', or 'NA'")
        return normalized

    @validates('date_of_birth')
    def validate_date_of_birth(self, key, value):
        if value is None:
            return value
        if value < date(1900, 1, 1):
            raise ValueError("date_of_birth cannot be before 1900-01-01")
        if value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return value

    @validates('age')
    def validate_age(self, key, value):
        if value is not None and value < 16:
            raise ValueError("Fighter age must be at least 16 or None if age is unknown")
        return value

    # Python-level validation — Record
    @validates('number_of_total_bouts', 'wins', 'losses', 'draws', 'no_contests')
    def validate_non_negative(self, key, value):
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value

    # Python-level validation — Stats
    @validates('overall_finish_rate')
    def validate_finish_rate(self, key, value):
        if value < 0.0 or value > 1.0:
            raise ValueError("overall_finish_rate must be between 0.0 and 1.0")
        return value

    def __repr__(self):
        return f"<Fighter(id={self.id}, name='{self.name}', sex='{self.sex}')>"