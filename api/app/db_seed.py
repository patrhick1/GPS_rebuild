"""
Database seeding script for GPS Assessment Platform.
Run this to populate the database with initial data (roles, types, question_types, etc.)
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.role import Role
from app.models.type import Type
from app.models.question_type import QuestionType
from app.models.gifts_passion import GiftsPassion
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.core.security import get_password_hash


def seed_roles(db: Session):
    """Seed roles table."""
    existing_roles = db.query(Role).count()
    if existing_roles > 0:
        print(f"Roles already seeded ({existing_roles} found)")
        return
    
    roles = Role.get_default_roles()
    for role_data in roles:
        db_role = Role(**role_data)
        db.add(db_role)
    
    db.commit()
    print(f"Seeded {len(roles)} roles")


def seed_types(db: Session):
    """Seed types table (Spiritual Gift, Influencing Style)."""
    existing_types = db.query(Type).count()
    if existing_types > 0:
        print(f"Types already seeded ({existing_types} found)")
        return
    
    types = Type.get_default_types()
    for type_data in types:
        db_type = Type(**type_data)
        db.add(db_type)
    
    db.commit()
    print(f"Seeded {len(types)} types")


def seed_question_types(db: Session):
    """Seed question_types table."""
    existing_types = db.query(QuestionType).count()
    if existing_types > 0:
        print(f"Question types already seeded ({existing_types} found)")
        return
    
    types = QuestionType.get_default_types()
    for type_data in types:
        db_type = QuestionType(**type_data)
        db.add(db_type)
    
    db.commit()
    print(f"Seeded {len(types)} question types")


def seed_gifts_passions(db: Session):
    """Seed gifts_passions table (19 spiritual gifts + 5 influencing styles)."""
    existing = db.query(GiftsPassion).count()
    if existing > 0:
        print(f"Gifts/Passions already seeded ({existing} found)")
        return
    
    # Get type IDs
    spiritual_gift_type = db.query(Type).filter(Type.name == "Spiritual Gift").first()
    influencing_style_type = db.query(Type).filter(Type.name == "Influencing Style").first()
    
    if not spiritual_gift_type or not influencing_style_type:
        print("Error: Types must be seeded before gifts/passions")
        return
    
    # Seed spiritual gifts
    gifts = GiftsPassion.get_default_gifts()
    for gift_data in gifts:
        db_gift = GiftsPassion(
            **gift_data,
            type_id=spiritual_gift_type.id,
            questions="",  # Will be populated later when questions are created
        )
        db.add(db_gift)
    
    # Seed influencing styles
    styles = GiftsPassion.get_default_influencing_styles()
    for style_data in styles:
        db_style = GiftsPassion(
            **style_data,
            type_id=influencing_style_type.id,
            questions="",
        )
        db.add(db_style)
    
    db.commit()
    print(f"Seeded {len(gifts)} spiritual gifts and {len(styles)} influencing styles")


def seed_test_data(db: Session):
    """Seed test organizations and users."""
    existing_users = db.query(User).count()
    if existing_users > 0:
        print(f"Test data already seeded ({existing_users} users found)")
        return
    
    # Get roles
    user_role = db.query(Role).filter(Role.name == "user").first()
    member_role = db.query(Role).filter(Role.name == "member").first()
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    master_role = db.query(Role).filter(Role.name == "master").first()
    
    # Create test organizations
    orgs = []
    for i in range(1, 4):
        org = Organization(
            name=f"Test Church {i}",
            city=f"City {i}",
            state="OH",
            country="USA",
            key=f"test-church-{i}",
        )
        db.add(org)
        orgs.append(org)
    
    db.commit()
    print(f"Created {len(orgs)} test organizations")
    
    # Create test users
    users_data = [
        # Independent users
        {"email": "user1@test.com", "first_name": "John", "last_name": "Doe", "role": user_role},
        {"email": "user2@test.com", "first_name": "Jane", "last_name": "Smith", "role": user_role},
        # Members
        {"email": "member1@test.com", "first_name": "Bob", "last_name": "Wilson", "role": member_role, "org": orgs[0]},
        {"email": "member2@test.com", "first_name": "Alice", "last_name": "Brown", "role": member_role, "org": orgs[0]},
        {"email": "member3@test.com", "first_name": "Charlie", "last_name": "Davis", "role": member_role, "org": orgs[1]},
        # Admins
        {"email": "admin1@test.com", "first_name": "Admin", "last_name": "One", "role": admin_role, "org": orgs[0]},
        {"email": "admin2@test.com", "first_name": "Admin", "last_name": "Two", "role": admin_role, "org": orgs[1]},
        {"email": "admin3@test.com", "first_name": "Admin", "last_name": "Three", "role": admin_role, "org": orgs[2]},
        # Master admin
        {"email": "master@test.com", "first_name": "Master", "last_name": "Admin", "role": master_role},
    ]
    
    for user_data in users_data:
        role = user_data.pop("role")
        org = user_data.pop("org", None)
        
        user = User(
            **user_data,
            password_hash=get_password_hash("password123"),
            status="active",
        )
        db.add(user)
        db.flush()  # Get user ID
        
        membership = Membership(
            user_id=user.id,
            organization_id=org.id if org else None,
            role_id=role.id,
        )
        db.add(membership)
    
    db.commit()
    print(f"Created {len(users_data)} test users")


def seed_all():
    """Run all seed functions."""
    # Create all tables first
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Starting database seeding...")
        seed_roles(db)
        seed_types(db)
        seed_question_types(db)
        seed_gifts_passions(db)
        seed_test_data(db)
        print("Database seeding completed!")
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
