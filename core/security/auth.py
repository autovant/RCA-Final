"""
Authentication and authorization module for RCA Engine.
Provides JWT token management and user authentication.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.config import settings
from core.db.models import User
from core.db.database import get_db
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class AuthService:
    """Service for authentication and authorization operations."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a password for storage.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Data to encode in the token
            expires_delta: Optional expiration time delta
            
        Returns:
            str: Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.security.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": settings.security.JWT_ISSUER,
            "aud": settings.security.JWT_AUDIENCE,
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.security.JWT_SECRET_KEY,
            algorithm=settings.security.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token.
        
        Args:
            data: Data to encode in the token
            
        Returns:
            str: Encoded JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=settings.security.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": settings.security.JWT_ISSUER,
            "aud": settings.security.JWT_AUDIENCE,
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.security.JWT_SECRET_KEY,
            algorithm=settings.security.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token to decode
            
        Returns:
            Dict[str, Any]: Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.security.JWT_SECRET_KEY,
                algorithms=[settings.security.JWT_ALGORITHM],
                audience=settings.security.JWT_AUDIENCE,
                issuer=settings.security.JWT_ISSUER
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        username: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            db: Database session
            username: Username or email
            password: Plain text password
            
        Returns:
            Optional[User]: User object if authentication successful, None otherwise
        """
        try:
            # Try to find user by username or email
            stmt = select(User).where(
                (User.username == username) | (User.email == username)
            )
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User not found: {username}")
                return None
            
            if not user.is_active:
                logger.warning(f"Inactive user attempted login: {username}")
                return None
            
            if not AuthService.verify_password(password, user.password_hash):
                logger.warning(f"Invalid password for user: {username}")
                return None
            
            # Update last login time
            user.last_login_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"User authenticated successfully: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    @staticmethod
    async def create_user(
        db: AsyncSession,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_superuser: bool = False
    ) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session
            username: Username
            email: Email address
            password: Plain text password
            full_name: Optional full name
            is_superuser: Whether user is a superuser
            
        Returns:
            User: Created user object
            
        Raises:
            HTTPException: If username or email already exists
        """
        try:
            # Check if username exists
            stmt = select(User).where(User.username == username)
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            
            # Check if email exists
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create new user
            user = User(
                username=username,
                email=email,
                password_hash=AuthService.get_password_hash(password),
                full_name=full_name,
                is_superuser=is_superuser,
                is_active=True
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"User created successfully: {username}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user"
            )
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            db: Database session
            username: Username
            
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        try:
            stmt = select(User).where(User.username == username)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    try:
        payload = AuthService.decode_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await AuthService.get_user_by_id(db, user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active user.
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current superuser.
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        User: Current superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Export commonly used items
__all__ = [
    "AuthService",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "pwd_context",
    "security",
]
