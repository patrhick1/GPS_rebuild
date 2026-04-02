from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    get_token_hash,
)
from app.core.config import settings
from app.models.user import User
from app.models.role import Role
from app.models.membership import Membership
from app.models.refresh_token import RefreshToken
from app.models.password_reset import PasswordResetToken
from app.schemas.user import UserCreate, UserLogin, ChurchAdminRegister, ChurchUpgrade
import secrets
import string
import re


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, user_data: UserCreate, organization_key: Optional[str] = None) -> User:
        """Register a new user."""
        # Check if email already exists
        existing_user = self.db.query(User).filter(User.email == user_data.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        
        # Create user
        db_user = User(
            email=user_data.email.lower(),
            password_hash=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone_number=user_data.phone_number,
            city=user_data.city,
            state=user_data.state,
            country=user_data.country,
            locale=user_data.locale,
            status="active",
        )
        self.db.add(db_user)
        self.db.flush()  # Get the user ID without committing
        
        # Create membership
        # Find the appropriate role
        if organization_key:
            # Check for organization and create member membership
            from app.models.organization import Organization
            org = self.db.query(Organization).filter(Organization.key == organization_key).first()
            if org:
                role = self.db.query(Role).filter(Role.name == "member").first()
                membership = Membership(
                    user_id=db_user.id,
                    organization_id=org.id,
                    role_id=role.id if role else None,
                )
            else:
                # Organization not found, create as independent user
                role = self.db.query(Role).filter(Role.name == "user").first()
                membership = Membership(
                    user_id=db_user.id,
                    organization_id=None,
                    role_id=role.id if role else None,
                )
        else:
            # Independent user
            role = self.db.query(Role).filter(Role.name == "user").first()
            membership = Membership(
                user_id=db_user.id,
                organization_id=None,
                role_id=role.id if role else None,
            )
        
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user

    def register_church_admin(self, data: ChurchAdminRegister) -> User:
        """Register a new church admin, creating the organization in one transaction."""
        from app.models.organization import Organization

        # Check email uniqueness
        existing = self.db.query(User).filter(User.email == data.email.lower()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        if not data.org_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Church name is required",
            )

        # Generate unique org key from church name
        base_key = re.sub(r'[^a-z0-9]+', '-', data.org_name.lower().strip()).strip('-')
        org_key = base_key
        counter = 1
        while self.db.query(Organization).filter(Organization.key == org_key).first():
            org_key = f"{base_key}-{counter}"
            counter += 1

        # Create user
        db_user = User(
            email=data.email.lower(),
            password_hash=get_password_hash(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            city=data.org_city,
            state=data.org_state,
            country=data.org_country,
            status="active",
        )
        self.db.add(db_user)
        self.db.flush()

        # Create organization
        org = Organization(
            name=data.org_name.strip(),
            key=org_key,
            city=data.org_city,
            state=data.org_state,
            country=data.org_country,
            status="active",
        )
        self.db.add(org)
        self.db.flush()

        # Create membership as primary admin with admin role
        role = self.db.query(Role).filter(Role.name == "admin").first()
        membership = Membership(
            user_id=db_user.id,
            organization_id=org.id,
            role_id=role.id if role else None,
            is_primary_admin=True,
        )
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def upgrade_to_church_admin(self, user: User, data: ChurchUpgrade) -> User:
        """Upgrade an existing logged-in user to church admin by creating their organization."""
        from app.models.organization import Organization

        if not data.org_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Church name is required",
            )

        # Generate unique org key from church name
        base_key = re.sub(r'[^a-z0-9]+', '-', data.org_name.lower().strip()).strip('-')
        org_key = base_key
        counter = 1
        while self.db.query(Organization).filter(Organization.key == org_key).first():
            org_key = f"{base_key}-{counter}"
            counter += 1

        # Create organization
        org = Organization(
            name=data.org_name.strip(),
            key=org_key,
            city=data.org_city,
            state=data.org_state,
            country=data.org_country,
            status="active",
        )
        self.db.add(org)
        self.db.flush()

        # Get admin role
        role = self.db.query(Role).filter(Role.name == "admin").first()

        # Check if user already belongs to a church
        existing_membership = next(
            (m for m in user.memberships if m.organization_id is not None), None
        )

        if existing_membership:
            if existing_membership.is_primary_admin:
                # Primary admins cannot leave without addressing their church first
                other_admins = self.db.query(Membership).filter(
                    Membership.organization_id == existing_membership.organization_id,
                    Membership.user_id != user.id,
                    Membership.role.has(name="admin"),
                    Membership.status == "active",
                ).count()

                if other_admins > 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You must transfer primary admin status to another administrator before creating a new church."
                    )

                other_members = self.db.query(Membership).filter(
                    Membership.organization_id == existing_membership.organization_id,
                    Membership.user_id != user.id,
                    Membership.status == "active",
                ).count()

                if other_members > 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You must promote a member to administrator and transfer primary status before creating a new church."
                    )

                # Alone in the church — cancel its Stripe subscription then detach
                from app.models.subscription import Subscription
                from app.services.stripe_service import stripe_service
                old_sub = self.db.query(Subscription).filter(
                    Subscription.organization_id == existing_membership.organization_id
                ).order_by(Subscription.created_at.desc()).first()
                if old_sub and old_sub.stripe_subscription_id and old_sub.status not in ("canceled", "incomplete_expired"):
                    try:
                        stripe_service.cancel_subscription(old_sub.stripe_subscription_id, at_period_end=False)
                        old_sub.status = "canceled"
                        self.db.flush()
                    except Exception:
                        pass  # Don't block the flow if Stripe cancel fails
            else:
                # Secondary admin or regular member — detach from old church
                existing_membership.organization_id = None
                self.db.flush()

        # Create new membership for the new org (user is now primary admin)
        membership = Membership(
            user_id=user.id,
            organization_id=org.id,
            role_id=role.id if role else None,
            is_primary_admin=True,
        )
        self.db.add(membership)

        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = self.db.query(User).filter(User.email == login_data.email.lower()).first()
        if not user:
            return None
        if not verify_password(login_data.password, user.password_hash):
            return None
        return user

    def create_tokens(self, user_id: UUID) -> dict:
        """Create access and refresh tokens for a user."""
        access_token = create_access_token(data={"sub": str(user_id)})
        refresh_token_str = create_refresh_token(data={"sub": str(user_id)})
        
        # Store refresh token hash in database (never store plaintext tokens)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db_refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=get_token_hash(refresh_token_str),
            expires_at=expires_at,
        )
        self.db.add(db_refresh_token)
        self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    def refresh_access_token(self, refresh_token_str: str) -> dict:
        """Refresh access token using refresh token."""
        from app.core.security import decode_token
        
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Check if refresh token hash exists and is valid
        db_token = self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == get_token_hash(refresh_token_str),
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        ).first()
        
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        
        user_id = payload.get("sub")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.status in ["locked", "deleted"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or disabled",
            )
        
        # Create new tokens
        return self.create_tokens(user.id)

    def revoke_refresh_token(self, refresh_token_str: str):
        """Revoke a refresh token (logout)."""
        db_token = self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == get_token_hash(refresh_token_str)
        ).first()
        
        if db_token:
            db_token.revoked = True
            self.db.commit()

    def create_password_reset_token(self, email: str) -> Optional[str]:
        """Create a password reset token for a user."""
        user = self.db.query(User).filter(User.email == email.lower()).first()
        if not user:
            return None
        
        # Generate random token
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
        
        # Store token
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )
        self.db.add(reset_token)
        self.db.commit()
        
        return token

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using a reset token."""
        reset_token = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.used == "N",
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        ).first()
        
        if not reset_token:
            return False
        
        # Update password
        user = self.db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            return False
        
        user.password_hash = get_password_hash(new_password)
        reset_token.used = "Y"
        
        # Revoke all refresh tokens for this user
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id
        ).update({"revoked": True})
        
        self.db.commit()
        return True

    def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        """Change password for a user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if not verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = get_password_hash(new_password)
        
        # Revoke all refresh tokens
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).update({"revoked": True})
        
        self.db.commit()
        return True
