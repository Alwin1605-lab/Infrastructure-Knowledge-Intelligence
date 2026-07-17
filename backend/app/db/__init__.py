"""MongoDB database module.

Provides async connection management using Motor and Beanie ODM.

Usage:
    from app.db import init_db, close_db
"""

from app.db.connection import init_db, close_db

__all__ = ["init_db", "close_db"]
