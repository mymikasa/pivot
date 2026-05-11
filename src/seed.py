from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.core.security import get_password_hash
from src.models.user import Role, User


def seed():
    db: Session = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is None:
            admin_role = Role(name="admin", description="管理员")
            db.add(admin_role)

        user_role = db.query(Role).filter(Role.name == "user").first()
        if user_role is None:
            user_role = Role(name="user", description="普通用户")
            db.add(user_role)

        db.commit()

        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user is None:
            admin_user = User(
                username="admin",
                email="admin@pivot.com",
                hashed_password=get_password_hash("admin123"),
                role_id=admin_role.id,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()

        print("Seed 完成")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
