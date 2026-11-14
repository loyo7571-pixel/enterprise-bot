from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models

SECRET_KEY = "super_secret_key" # Used to sign the JWT
ALGORITHM = "HS256"                         # The math algorithm for the token
ACCESS_TOKEN_EXPIRE_MINUTES = 30            # Token dies after 30 mins

# 1. Hashing: This turns "mypassword" into "$2b$12$..." so no one can read it.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. OAuth2 Scheme: This tells FastAPI to look in the HTTP header for "Authorization: Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 3. Check Password: Compares plain text with the hash
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 4. Hash Password: Creates the hash for a new user
def get_password_hash(password):
    return pwd_context.hash(password)

# 5. Create Token: Generates the JWT string
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire}) # Add expiry time to the token
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 6. Get Current User: The "Bouncer"
# This function runs BEFORE a protected endpoint.
# It reads the token, decodes it, and finds the user in the DB.
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    
    try:
        # Decode the token using our Secret Key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub") # "sub" is standard for the user identifier
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Find the user in the DB
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user