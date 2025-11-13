# Cấu Trúc Project

```
goline/
│
├── 📄 README.md                      # Báo cáo chi tiết, kiến trúc, tối ưu
├── 📄 INSTALL.md                     # Hướng dẫn cài đặt nhanh
├── 📄 STRUCTURE.md                   # File này - cấu trúc project
├── 📄 requirements.txt               # Dependencies Python
├── 📄 .gitignore                     # Git ignore patterns
│
├── 🐍 run_final_clean.py             # ⭐ MAIN: Agent + FastAPI server
├── 🐍 llm_agent.py                   # ⭐ LLM abstraction layer
├── 🐍 format_table_clean.py          # Format output với table
├── 🐍 hoi_final_clean.py             # CLI - Hỏi 1 câu
├── 🐍 benchmark.py                   # ⭐ Test tự động từ Excel
│
├── 📊 AI_Intern_test_questions.xlsx  # 13 câu hỏi test
├── 📊 benchmark_results.xlsx         # ⭐ Kết quả test (thời gian, answer)
└── 📋 AI Test_LLM.docx               # Yêu cầu đề bài gốc
```

---

## 📂 Chi Tiết Files

### Core Files (⭐ Quan trọng nhất)

#### 1. `run_final_clean.py` (13.5 KB)
**Main Agent code**
- Class `Agent`: Xử lý câu hỏi, gọi LLM, fetch data
- Class `VNStockService`: Fetch data từ VnStock API + cache + parallel
- FastAPI endpoints: `/ask`, `/health`, `/price/history`
- **Tối ưu:**
  - LRU Cache cho API calls
  - Parallel fetching với ThreadPoolExecutor
  - Vectorized datetime conversion

#### 2. `llm_agent.py` (3.3 KB)
**LLM Abstraction Layer**
- Class `LLMAgent`: Wrapper cho LLM providers
- Support Gemini (có thể thêm OpenAI, Claude sau)
- Tự động đọc API key từ env
- **Lợi ích:** Dễ thay đổi LLM provider

#### 3. `benchmark.py` (2.7 KB)
**Automated Testing**
- Đọc questions từ Excel
- Chạy từng câu, đo thời gian
- Lưu kết quả vào `benchmark_results.xlsx`
- **Output:** Question, Expected, Actual, Time, Error

#### 4. `README.md` (12.8 KB)
**Báo cáo nộp bài chi tiết**
- Yêu cầu đã hoàn thành
- 4 kỹ thuật tối ưu (code + giải thích)
- Benchmark results & analysis
- Kiến trúc hệ thống
- Hướng dẫn sử dụng

---

### Supporting Files

#### `format_table_clean.py` (5.2 KB)
Format output với table markdown đẹp

#### `hoi_final_clean.py` (1.2 KB)
CLI tool để hỏi 1 câu nhanh

#### `requirements.txt` (502 B)
List tất cả Python dependencies

#### `INSTALL.md` (1.3 KB)
Hướng dẫn cài đặt và chạy nhanh

---

## 🔄 Luồng Hoạt Động

```
User Question
    ↓
[hoi_final_clean.py] or [FastAPI /ask] or [benchmark.py]
    ↓
[Agent.handle()] in run_final_clean.py
    ↓
┌─────────────────────────────────┐
│ 1. LLMAgent._analyze_question() │ → Gemini: Parse JSON
│    → Extract: action, symbols   │
│    → Extract: time_phrase        │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 2. VNStockService.fetch_data()  │
│    → LRU Cache hit?              │
│    → Parallel fetch (3-5x fast) │
│    → Calc SMA/RSI if needed     │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 3. LLMAgent._generate_answer()  │ → Gemini: Generate text
│    → Natural language response  │
└─────────────────────────────────┘
    ↓
[format_answer_with_table()]
    ↓
JSON Response: {answer, data, meta}
```

---

## 🎯 Files Quan Trọng Nhất (Nộp Bài)

1. **README.md** - Báo cáo đầy đủ
2. **run_final_clean.py** - Main code
3. **benchmark.py** - Test automation
4. **benchmark_results.xlsx** - Kết quả
5. **llm_agent.py** - LLM abstraction
6. **requirements.txt** - Dependencies
7. **INSTALL.md** - Hướng dẫn cài đặt

---

## 📊 Thống Kê Code

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| run_final_clean.py | ~430 | 13.5KB | Main Agent + API |
| llm_agent.py | ~100 | 3.3KB | LLM wrapper |
| format_table_clean.py | ~150 | 5.2KB | Table formatter |
| hoi_final_clean.py | ~40 | 1.2KB | CLI tool |
| benchmark.py | ~80 | 2.7KB | Testing |
| **TOTAL** | **~800** | **26KB** | **Clean & Optimized** |

---

