#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script benchmark để test hiệu suất của hệ thống
"""
import sys
import os
import time
import pandas as pd

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['GEMINI_API_KEY'] = 'API'

from run_final_clean import Agent

def main():
    print("Đang đọc file output.xlsx...\n")
    df_questions = pd.read_excel("AI_Intern_test_questions.xlsx")
    agent = Agent()

    results = []

    for idx, row in df_questions.iterrows():
        question = row['question']
        expected = row['expected_answer']

        print(f"\nCâu {idx + 1}/{len(df_questions)}: {question}")
        print("-" * 80)

        # Đo thời gian
        start_time = time.time()

        try:
            result = agent.handle(question, use_llm=True)
            actual_answer = result.get("answer", "Không có câu trả lời")
            error = None
        except Exception as e:
            actual_answer = f"LỖI: {str(e)}"
            error = str(e)

        end_time = time.time()
        elapsed = end_time - start_time

        # Hiển thị kết quả
        print(f"Thời gian: {elapsed:.2f}s")
        print(f"Câu trả lời: {actual_answer[:200]}..." if len(actual_answer) > 200 else f"Câu trả lời: {actual_answer}")

        # Lưu kết quả
        results.append({
            'question': question,
            'expected_answer': expected,
            'actual_answer': actual_answer,
            'time_seconds': round(elapsed, 2),
            'error': error
        })

        print("=" * 80)

    # Xuất kết quả ra Excel
    df_results = pd.DataFrame(results)
    output_file = 'benchmark_results.xlsx'
    df_results.to_excel(output_file, index=False, engine='openpyxl')

    # Thống kê
    print("\n" + "=" * 80)
    print("THỐNG KÊ TỔNG QUAN")
    print("=" * 80)
    print(f"Tổng số câu hỏi: {len(results)}")
    print(f"Tổng thời gian: {sum(r['time_seconds'] for r in results):.2f}s")
    print(f"Thời gian trung bình: {sum(r['time_seconds'] for r in results) / len(results):.2f}s")
    print(f"Thời gian nhanh nhất: {min(r['time_seconds'] for r in results):.2f}s")
    print(f"Thời gian chậm nhất: {max(r['time_seconds'] for r in results):.2f}s")
    print(f"Số câu lỗi: {sum(1 for r in results if r['error'] is not None)}")
    print(f"\nKết quả đã lưu vào: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
