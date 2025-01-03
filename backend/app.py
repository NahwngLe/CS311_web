from fastapi import FastAPI, UploadFile, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional
import os
from utils import users_collection, hash_password, verify_password, create_jwt, decode_jwt, get_csv, quizzes_collection

app = FastAPI()

security = HTTPBearer()

# Cấu hình CORS cho phép frontend từ mọi nguồn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

class User(BaseModel):
    _id: str
    username: str
    password: str
    profile: Optional[dict] = {"email": "", "birthday": "","phone": "", "address": ""}
    quizzes: Optional[List[str]] = []

    class Config:
        json_encoders = {
            ObjectId: str
        }

class Login(BaseModel):
    username: str
    password: str

class Quiz(BaseModel):
    _id: str
    quiz_name: str
    questions: List[dict]
    attempts: Optional[List[dict]] = [] # Lưu thông tin về các lần thử quiz của user

    class Config:
        json_encoders = {
            ObjectId: str
        }

class Question(BaseModel):
    question_text: str
    options: List[str]
    correct_answer: str

def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token missing")
    
    token = authorization.split("Bearer ")[-1]

    if not token:
        raise HTTPException(status_code=401, detail="Token missing")
    
    user_data = decode_jwt(token)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_data

# API đăng ký
@app.post("/api/register")
async def register_user(user: User):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username đã tồn tại")

    password_hash = hash_password(user.password)
    users_collection.insert_one({
        "username": user.username,
        "password": password_hash,
        "profile": user.profile,
        "quizzes": []
    })
    return {"message": "Đăng ký thành công"}

# API đăng nhập
@app.post("/api/login")
async def login_user(user: Login):
    db_user = users_collection.find_one({"username": user.username})
    
    if not db_user:
        raise HTTPException(status_code=400, detail="Tên người dùng không tồn tại")

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Mật khẩu không chính xác")

    token = create_jwt({"username": user.username})
    
    return {"token": token}


# API đăng xuất
@app.post("/api/logout")
async def logout():
    return {"message": "Đăng xuất thành công"}

# API lấy danh sách quizzes
@app.get("/api/quizzes", response_model=List[Quiz])
async def get_quizzes(current_user=Depends(get_current_user)):
    # Lấy thông tin người dùng từ cơ sở dữ liệu
    user = users_collection.find_one({"username": current_user["username"]})
    
    # Kiểm tra nếu người dùng không tồn tại
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Lấy danh sách các quiz_id của người dùng
    quiz_ids = user.get("quizzes", [])
    
    # Lọc các quiz từ quizzes_collection dựa trên quiz_id của người dùng
    all_quizzes = quizzes_collection.find()  # Lấy tất cả các quiz
    quizzes = [
        {**quiz, '_id': str(quiz['_id'])}  # Chuyển đổi _id thành chuỗi
        for quiz in all_quizzes if str(quiz['_id']) in quiz_ids
    ]
    
    return quizzes

# API thêm quiz
@app.post("/api/quizzes", response_model=Quiz)
async def create_quiz(quiz: Quiz, current_user=Depends(get_current_user)):
    # Lấy thông tin người dùng từ cơ sở dữ liệu
    user = users_collection.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Kiểm tra nếu quiz đã tồn tại trong danh sách quizzes của người dùng
    if "quizzes" not in user or any(existing_quiz["_id"] == quiz._id for existing_quiz in user["quizzes"]):
        raise HTTPException(status_code=400, detail="Quiz đã tồn tại.")
    
    # Thêm quiz vào cơ sở dữ liệu
    result = quizzes_collection.insert_one(quiz.dict())
    quiz._id = str(result.inserted_id)

    # Thêm quiz mới vào danh sách quizzes của người dùng
    users_collection.update_one(
        {"username": current_user["username"]},
        {"$push": {"quizzes": quiz._id}}
    )

    print(quiz)

    return quiz

# API sửa quiz
@app.put("/api/quizzes/{quiz_name}", response_model=Quiz)
async def update_quiz(quiz_name: str, quiz: Quiz, current_user=Depends(get_current_user)):
    # Tìm người dùng hiện tại
    user = users_collection.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    
    # Giả sử user.get("quizzes", []) trả về danh sách các chuỗi
    quiz_ids = [ObjectId(id_str) for id_str in user.get("quizzes", [])]

    # Tìm quiz theo tên quiz và thuộc quyền sở hữu của người dùng
    existing_quiz = quizzes_collection.find_one({"quiz_name": quiz_name, "_id": {"$in": quiz_ids}})

    # Cập nhật quiz trong MongoDB
    quizzes_collection.update_one(
        {"_id": existing_quiz["_id"]},
        {"$set": {"questions": quiz.questions}}
    )
    
    existing_quiz["questions"] = quiz.questions
    return existing_quiz


# API xóa quiz
@app.delete("/api/quizzes/{quiz_name}")
async def delete_quiz(quiz_name: str, current_user=Depends(get_current_user)):
    # Tìm người dùng hiện tại
    user = users_collection.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    
    # Giả sử user.get("quizzes", []) trả về danh sách các chuỗi
    quiz_ids = [ObjectId(id_str) for id_str in user.get("quizzes", [])]

    # Tìm quiz theo tên quiz và thuộc quyền sở hữu của người dùng
    quiz = quizzes_collection.find_one({"quiz_name": quiz_name, "_id": {"$in": quiz_ids}})
    
    # Xóa quiz trong MongoDB
    quizzes_collection.delete_one({"_id": quiz["_id"]})
    
    # Xóa ID quiz khỏi danh sách `user.quizzes`
    users_collection.update_one(
        {"username": current_user["username"]},
        {"$pull": {"quizzes": str(quiz["_id"])}}
    )
    
    return {"message": f"Quiz '{quiz_name}' đã bị xóa thành công."}

#API xem quiz
@app.get("/api/quizzes/{quiz_name}")
async def get_quiz(quiz_name: str, current_user=Depends(get_current_user)):
    # Tìm người dùng hiện tại
    user = users_collection.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    
    # Giả sử user.get("quizzes", []) trả về danh sách các chuỗi
    quiz_ids = [ObjectId(id_str) for id_str in user.get("quizzes", [])]

    # Tìm quiz theo tên quiz và thuộc quyền sở hữu của người dùng
    quiz = quizzes_collection.find_one({"quiz_name": quiz_name, "_id": {"$in": quiz_ids}})

    quiz["_id"] = str(quiz["_id"])
    quiz["questions"] = quiz["questions"]
    
    return quiz

# API gửi bài làm quiz
@app.post("/api/quizzes/{quiz_name}/attempt")
async def attempt_quiz(quiz_name: str, answers: List[str], current_user=Depends(get_current_user)):
    quiz = quizzes_collection.find_one({"quiz_name": quiz_name})
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz")

    # Tính điểm
    correct_answers = [q["answer"] for q in quiz["questions"]]
    score = sum(1 for i, ans in enumerate(answers) if ans == correct_answers[i])

    # Lưu kết quả làm quiz
    attempt = {
        "username": current_user["username"],
        "answers": answers,
        "score": score,
    }
    quizzes_collection.update_one(
        {"quiz_name": quiz_name},
        {"$push": {"attempts": attempt}}
    )

    return {"score": score, "total": len(correct_answers), "answers": correct_answers}

# API hiển thị lịch sử làm quiz
@app.get("/api/quizzes/{quiz_name}/history")
async def get_quiz_history(quiz_name: str, current_user=Depends(get_current_user)):
    quiz = quizzes_collection.find_one({"quiz_name": quiz_name})
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz")

    history = [
        attempt for attempt in quiz.get("attempts", [])
        if attempt["username"] == current_user["username"]
    ]
    return history


# API xử lý PDF
@app.post("/upload")
async def upload_pdf(file: UploadFile):
    upload_folder = "static"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    file_location = os.path.join(upload_folder, file.filename)

    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())
    
    return {"filename": file.filename, "file_location": file_location}

@app.post("/process-pdf")
async def process_pdf(file: UploadFile, current_user=Depends(get_current_user)):
    # Tìm người dùng hiện tại
    user = users_collection.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    
    upload_folder = "static"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    file_location = os.path.join(upload_folder, file.filename)

    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())
    
    csv_file = get_csv(file_location, user)
    csv_filename = os.path.basename(csv_file)

    return {"csvFilename": csv_filename}