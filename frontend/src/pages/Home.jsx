import React, { useState, useEffect } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";

const Home = () => {
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const navigate = useNavigate();

  useEffect(() => {
    const fetchQuizzes = async () => {
      setLoading(true);
      try {
        const response = await axios.get("http://localhost:8000/api/quizzes", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        setQuizzes(response.data);
      } catch (err) {
        setError("Không thể tải danh sách quiz.");
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchQuizzes();
    }
  }, [token]);

  const handleDelete = async (quizName) => {
    try {
      await axios.delete(`http://localhost:8000/api/quizzes/${quizName}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setQuizzes(quizzes.filter((quiz) => quiz.quiz_name !== quizName));
    } catch (err) {
      setError("Không thể xóa quiz.");
    }
  };

  const handleCardClick = (quizName) => {
    navigate(`/quiz/${quizName}`);
  };

  const handleLogout = () => {
    localStorage.removeItem("token"); // Xóa token khi đăng xuất
    setToken(null);
    navigate("/login"); // Chuyển hướng về trang đăng nhập
  };

  return (
    <div className="flex flex-col items-center min-h-screen bg-gradient-to-r from-blue-400 to-purple-500 p-6">
      <h1 className="text-4xl font-bold mb-6">Quản lý Câu Hỏi Quiz</h1>
      <button
        onClick={handleLogout}
        className="bg-red-500 text-white py-2 px-6 rounded-lg shadow mb-4"
      >
        Đăng xuất
      </button>
      <div className="grid grid-cols-3 gap-6 w-full max-w-7xl">
        <div className="col-span-2 bg-white p-6 rounded-lg shadow">
          <h2 className="text-2xl font-bold mb-4">Danh sách Quiz</h2>
          {loading ? (
            <p>Đang tải...</p>
          ) : error ? (
            <p className="text-red-500">{error}</p>
          ) : quizzes.length === 0 ? (
            <p>Không có quiz nào.</p>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {quizzes.map((quiz) => (
                <div
                  key={quiz.quiz_name}
                  className="bg-gray-50 p-4 rounded-lg shadow-sm border cursor-pointer"
                  onClick={() => handleCardClick(quiz.quiz_name)}
                >
                  <h3 className="text-lg font-semibold">{quiz.quiz_name}</h3>
                  <div className="flex justify-between mt-4">
                    <button
                      onClick={(e) => {
                        e.stopPropagation(); // Ngăn chặn sự kiện click trên card
                        handleDelete(quiz.quiz_name);
                      }}
                      className="bg-red-500 text-white py-1 px-4 rounded hover:bg-red-700 transition"
                    >
                      Xóa
                    </button>
                    <Link to={`/edit/${quiz.quiz_name}`}>
                      <button
                        onClick={(e) => e.stopPropagation()}
                        className="bg-yellow-500 text-white py-1 px-4 rounded hover:bg-yellow-700 transition"
                      >
                        Sửa
                      </button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="flex flex-col items-center gap-4">
          <Link
            to="/add-quiz"
            className="bg-green-500 text-white py-3 px-6 rounded-lg shadow hover:bg-green-700 transition w-full text-center"
          >
            Thêm Quiz
          </Link>
          <div className="bg-blue-500 text-white p-6 rounded-lg shadow hover:bg-blue-700 transition w-full text-center">
            <h3 className="text-lg font-semibold">Tải lên PDF</h3>
            <p>Chọn để tải lên PDF và tạo câu hỏi.</p>
            <Link to="/upload">
              <button className="mt-4 bg-white text-blue-500 py-2 px-4 rounded-lg hover:bg-gray-100 transition">
                Tải lên
              </button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
