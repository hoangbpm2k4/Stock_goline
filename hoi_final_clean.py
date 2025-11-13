import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['GEMINI_API_KEY'] = 'AIzaSyAVqeAGwful1828vSLU34p8Bi7kVioyMvU'

from run_final_clean import Agent

def main():
    if len(sys.argv) < 2:
        print("Cách dùng: python hoi_final.py \"Câu hỏi của bạn\"")
        print("\nVí dụ:")
        print('  python hoi_final.py "Lấy dữ liệu OHLCV 10 ngày gần nhất HPG"')
        print('  python hoi_final.py "RSI 14 của VIC trong 2 tuần"')
        print('  python hoi_final.py "So sánh giá VCB và HPG trong 1 tháng"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print("🔍 Đang xử lý...\n")

    agent = Agent()
    result = agent.handle(question, use_llm=True)

    print("=" * 80)
    print("💡 TRẢ LỜI:")
    print("=" * 80)
    print(result.get("answer", "Không có câu trả lời"))
    print("=" * 80)

if __name__ == "__main__":
    main()
