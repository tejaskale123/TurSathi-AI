from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base class.
    All database models will inherit from this Base.
    """
    pass
