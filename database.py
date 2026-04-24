from models import SessionLocal, User
from hashlib import sha256

def create_user(username: str, password: str) -> User | None:
    """Создаёт пользователя. Возвращает None если username занят."""
    db = SessionLocal()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        return None

    hashed = sha256((password + "pigeon_salt_2024").encode()).hexdigest()
    user = User(username=username, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

def check_user(username: str, password: str) -> bool:
    """Проверяет пароль. True если верно."""
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user:
        return False
    hashed = sha256((password + "pigeon_salt_2024").encode()).hexdigest()
    return user.password_hash == hashed

def update_profile(username: str, first_name: str, last_name: str, nickname: str):
    """Обновляет профиль пользователя."""
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.first_name = first_name
        user.last_name = last_name
        user.nickname = nickname
        db.commit()
    db.close()

def get_profile(username: str) -> dict:
    """Возвращает профиль пользователя."""
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if user:
        return {
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "nickname": user.nickname or ""
        }
    return {}
