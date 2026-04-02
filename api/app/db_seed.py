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
from app.models.question import Question
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
        )
        db.add(db_gift)
    
    # Seed influencing styles
    styles = GiftsPassion.get_default_influencing_styles()
    for style_data in styles:
        db_style = GiftsPassion(
            **style_data,
            type_id=influencing_style_type.id,
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
        # Admins (first admin of each org is primary)
        {"email": "admin1@test.com", "first_name": "Admin", "last_name": "One", "role": admin_role, "org": orgs[0], "is_primary_admin": True},
        {"email": "admin2@test.com", "first_name": "Admin", "last_name": "Two", "role": admin_role, "org": orgs[1], "is_primary_admin": True},
        {"email": "admin3@test.com", "first_name": "Admin", "last_name": "Three", "role": admin_role, "org": orgs[2], "is_primary_admin": True},
        # Secondary admin for testing
        {"email": "admin2nd@test.com", "first_name": "Secondary", "last_name": "Admin", "role": admin_role, "org": orgs[0], "is_primary_admin": False},
        # Master admin
        {"email": "master@test.com", "first_name": "Master", "last_name": "Admin", "role": master_role},
    ]
    
    for user_data in users_data:
        role = user_data.pop("role")
        org = user_data.pop("org", None)
        is_primary_admin = user_data.pop("is_primary_admin", False)
        
        user = User(
            **user_data,
            password_hash=get_password_hash("TestPass#2024"),
            status="active",
        )
        db.add(user)
        db.flush()  # Get user ID
        
        membership = Membership(
            user_id=user.id,
            organization_id=org.id if org else None,
            role_id=role.id,
            is_primary_admin=is_primary_admin,
        )
        db.add(membership)
    
    db.commit()
    print(f"Created {len(users_data)} test users")


def seed_questions(db: Session):
    """Seed questions from CSV file."""
    from app.models.question import Question
    import csv
    import os
    
    # Get type IDs
    spiritual_gift_type = db.query(Type).filter(Type.name == "Spiritual Gift").first()
    influencing_style_type = db.query(Type).filter(Type.name == "Influencing Style").first()
    story_type = db.query(Type).filter(Type.name == "Story").first()
    
    # Get question type IDs
    likert_type = db.query(QuestionType).filter(QuestionType.type == "likert").first()
    multiple_choice_type = db.query(QuestionType).filter(QuestionType.type == "multiple_choice").first()
    text_type = db.query(QuestionType).filter(QuestionType.type == "text").first()
    
    if not all([spiritual_gift_type, influencing_style_type, story_type, likert_type, multiple_choice_type, text_type]):
        print("Error: Required types and question_types must be seeded first")
        return
    
    # Seed GPS questions if not already present
    existing_gps = db.query(Question).filter(Question.instrument_type == "gps").count()
    if existing_gps == 0:
        # Read questions from CSV
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'gps_questions.csv')
        if not os.path.exists(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'gps_questions.csv')
        
        if os.path.exists(csv_path):
            count = 0
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Map GPSType to type_id
                    gpstype = int(row['GPSType'])
                    if gpstype == 1:
                        type_id = spiritual_gift_type.id
                    elif gpstype == 2:
                        type_id = influencing_style_type.id
                    elif gpstype == 3:
                        type_id = story_type.id
                    else:
                        type_id = spiritual_gift_type.id
                    
                    # Map QuestionType to question_type_id
                    question_type_id = int(row['QuestionType'])
                    if question_type_id == 1:
                        qtype_id = likert_type.id
                    elif question_type_id == 2:
                        qtype_id = multiple_choice_type.id
                    elif question_type_id == 3:
                        qtype_id = text_type.id
                    else:
                        qtype_id = likert_type.id
                    
                    question = Question(
                        question=row['Question'],
                        question_es=None,  # Spanish version in separate CSV
                        order=int(row['SortOrder']),
                        passion_type=row['PassionType'] if row['PassionType'] else None,
                        passion_type_es=None,
                        default_text=row['AnswerDefault'] if row['AnswerDefault'] else None,
                        default_text_es=None,
                        summary=row['SummaryText'] if row['SummaryText'] else None,
                        summary_es=None,
                        type_id=type_id,
                        question_type_id=qtype_id,
                        instrument_type="gps",
                    )
                    db.add(question)
                    count += 1
            
            db.commit()
            print(f"Seeded {count} GPS questions")
        else:
            print(f"Warning: gps_questions.csv not found at {csv_path}")
    else:
        print(f"GPS questions already seeded ({existing_gps} found)")

    # Load Spanish translations for GPS questions
    # Match by section + per-section question number (robust against text differences)
    spanish_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'gps_questions_spanish.csv')
    if not os.path.exists(spanish_csv_path):
        spanish_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'gps_questions_spanish.csv')

    if os.path.exists(spanish_csv_path):
        # Build ordered maps: section name → {per-section number → Question}
        gift_qs = (
            db.query(Question)
            .filter(Question.instrument_type == "gps", Question.type_id == spiritual_gift_type.id)
            .order_by(Question.order)
            .all()
        )
        infl_qs = (
            db.query(Question)
            .filter(Question.instrument_type == "gps", Question.type_id == influencing_style_type.id)
            .order_by(Question.order)
            .all()
        )
        section_map = {
            "Gifts":             {i + 1: q for i, q in enumerate(gift_qs)},
            "Influencing Style": {i + 1: q for i, q in enumerate(infl_qs)},
        }

        updated = skipped = 0
        with open(spanish_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                section = row['Section'].strip()
                spanish_text = row['Spanish'].strip()
                if not spanish_text:
                    continue
                try:
                    num = int(row['Question'])
                except (ValueError, KeyError):
                    skipped += 1
                    continue
                q = section_map.get(section, {}).get(num)
                if q:
                    q.question_es = spanish_text
                    updated += 1
                else:
                    skipped += 1

        db.commit()
        print(f"Updated {updated} GPS questions with Spanish translations ({skipped} skipped)")
    else:
        print(f"Warning: gps_questions_spanish.csv not found at {spanish_csv_path}")
    
    # Seed MyImpact questions if not already present
    existing_myimpact = db.query(Question).filter(Question.instrument_type == "myimpact").count()
    if existing_myimpact == 0:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'myimpact_questions.csv')
        if not os.path.exists(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'myimpact_questions.csv')
        
        if os.path.exists(csv_path):
            count = 0
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # MyImpact uses Character/Calling sections mapped to types
                    section = row['Section']
                    if section == "Character":
                        type_id = spiritual_gift_type.id  # Character maps to Spiritual Gift type
                    else:  # Calling
                        type_id = story_type.id  # Calling maps to Story type
                    
                    # Use sequential global order: Character 1-9, Calling 10-17
                    # CSV SortOrder is per-section (1-9 and 1-8), so offset Calling by 9
                    sort_order = int(row['SortOrder'])
                    global_order = sort_order if section == "Character" else sort_order + 9

                    question = Question(
                        question=row['Question'],
                        question_es=None,
                        order=global_order,
                        passion_type=None,
                        passion_type_es=None,
                        default_text=row.get('BibleRef'),
                        default_text_es=None,
                        summary=None,
                        summary_es=None,
                        type_id=type_id,
                        question_type_id=likert_type.id,  # All MyImpact questions are likert 1-10
                        instrument_type="myimpact",
                        section=section,
                    )
                    db.add(question)
                    count += 1
            
            db.commit()
            print(f"Seeded {count} MyImpact questions")
        else:
            print(f"Warning: myimpact_questions.csv not found at {csv_path}")
    else:
        print(f"MyImpact questions already seeded ({existing_myimpact} found)")


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
        seed_questions(db)  # Add questions seeding
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
