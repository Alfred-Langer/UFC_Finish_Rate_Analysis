# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from models.base import Base
# from contextlib import contextmanager
# from config import DATABASE_URL, SQL_ECHO

# # Create engine once
# if DATABASE_URL is None:
#     raise RuntimeError("DATABASE_URL must be set in environment variables.")
# engine = create_engine(DATABASE_URL, echo=SQL_ECHO)

# # Session factory
# SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# # Context manager for sessions
# @contextmanager
# def get_db_session():
#     session = SessionLocal()
#     try:
#         yield session
#     except Exception:
#         session.rollback()
#         raise
#     finally:
#         session.close()

