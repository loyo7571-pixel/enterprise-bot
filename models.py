from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# 1. The User Table
class User(Base):
    __tablename__ = "users" # The actual name of the table in Postgres

    # Columns
    id = Column(Integer, primary_key=True, index=True) # Auto-incrementing ID
    email = Column(String, unique=True, index=True)    # Email must be unique
    hashed_password = Column(String)                   # We NEVER store plain passwords
    
    # Relationship: This links the User to their ChatHistory.
    # It doesn't create a column; it's a Python shortcut to fetch history.
    history = relationship("ChatHistory", back_populates="owner")

# 2. The ChatHistory Table
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    answer = Column(Text)
    
    # Foreign Key: This creates a link to the 'users' table.
    # It means: "This chat belongs to a specific user."
    user_id = Column(Integer, ForeignKey("users.id"))

    # Relationship back to the user
    owner = relationship("User", back_populates="history")