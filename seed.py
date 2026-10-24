from database import SessionLocal
from models import User

# 1. Open a database session
db = SessionLocal()

# 2. Check if our dummy user already exists
test_user = db.query(User).filter(User.email == "test@test.com").first()

if not test_user:
    print("Creating Test User...")
    
    # 3. Create the User
    new_user = User(
        username="test_user", 
        email="test@test.com", 
        hashed_password="fake_password"
    )
    db.add(new_user)
    db.commit() 
    db.refresh(new_user) 
    
    print(f"Success! Test User created with ID: {new_user.id}")
else:
    print("Test User already exists in the database!")

db.close()