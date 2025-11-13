# Hướng Dẫn Cài Đặt & Chạy

## 📦 Cài Đặt

### 1. Clone hoặc Extract code

```bash
cd goline/
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình API Key

**Windows:**
```bash
set GEMINI_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY=your_api_key_here
```

Hoặc sửa trực tiếp trong file `benchmark.py` dòng 17:
```python
os.environ['GEMINI_API_KEY'] = 'your_api_key_here'
```

---

## 🚀 Chạy

### A. CLI - Hỏi 1 câu

```bash
python hoi_final_clean.py "Lấy dữ liệu OHLCV 10 ngày gần nhất HPG"
```

### B. REST API - FastAPI Server

```bash
# Start server
uvicorn run_final_clean:app --reload --port 8000

# Test
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Giá VCB 5 ngày", "use_llm": true}'
```

### C. Benchmark Test - Chạy tất cả câu hỏi

```bash
python benchmark.py
```

**Output:** `benchmark_results.xlsx`

---

## 📋 Yêu Cầu Hệ Thống

- Python 3.12+
- Internet connection (gọi Gemini API và VnStock API)
- Windows/Linux/Mac

---

## 🔧 Troubleshooting

### Lỗi: "GEMINI_API_KEY không tồn tại"
→ Set environment variable hoặc sửa trực tiếp trong code

### Lỗi: "ModuleNotFoundError"
→ Chạy: `pip install -r requirements.txt`

### Lỗi encoding trên Windows
→ Đã xử lý tự động trong code với UTF-8

---

Xem thêm chi tiết trong [README.md](README.md)
