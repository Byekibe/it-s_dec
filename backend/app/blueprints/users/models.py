"""
User models
"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from app.core.models import BaseModel


class User(BaseModel):
    """
    Global user model representing a person who can log in.
    A user can belong to multiple tenants.
    """
    __tablename__ = 'users'

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)

    # Relationships
    # Note: foreign_keys specified to resolve ambiguity with invited_by column
    tenant_memberships = relationship(
        'TenantUser',
        back_populates='user',
        cascade='all, delete-orphan',
        foreign_keys='TenantUser.user_id'
    )
    store_assignments = relationship(
        'StoreUser',
        back_populates='user',
        cascade='all, delete-orphan',
        foreign_keys='StoreUser.user_id'
    )
    role_assignments = relationship(
        'UserRole',
        back_populates='user',
        cascade='all, delete-orphan',
        foreign_keys='UserRole.user_id'
    )

    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'
