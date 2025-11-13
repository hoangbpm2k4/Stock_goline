#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import re, json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from io import StringIO

import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from vnstock import Company, Quote
from format_table_clean import format_answer_with_table
from llm_agent import LLMAgent

class APITraceLogger:
    def __init__(self, trace_file="api_trace.json"):
        self.trace_file = trace_file
        self.trace_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": "",
            "gemini_analysis": {},
            "api_calls": [],
            "data_summary": {},
            "final_answer": ""
        }

    def set_question(self, question: str):
        self.trace_data["question"] = question

    def set_analysis(self, analysis: dict):
        self.trace_data["gemini_analysis"] = analysis

    def add_api_call(self, api_name: str, params: dict, result_summary: str):
        self.trace_data["api_calls"].append({"api": api_name, "params": params, "result": result_summary})

    def set_data_summary(self, summary: dict):
        self.trace_data["data_summary"] = summary

    def set_answer(self, answer: str):
        self.trace_data["final_answer"] = answer

    def save(self):
        with open(self.trace_file, 'w', encoding='utf-8') as f:
            json.dump(self.trace_data, f, ensure_ascii=False, indent=2)

trace = APITraceLogger()

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()

def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_range_from_phrase(phrase: str, now: Optional[datetime] = None) -> Tuple[str, str]:
    now = now or datetime.now()
    m = re.search(r"(\d+)\s*(ngày|tuần|tháng|quý|nam|năm)", phrase, flags=re.I)
    if not m:
        start = now - timedelta(days=30)
        return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")

    n = int(m.group(1))
    unit = m.group(2).lower()

    if unit.startswith("ngày"):
        start = now - timedelta(days=n)
    elif unit.startswith("tuần"):
        start = now - timedelta(weeks=n)
    elif unit.startswith("tháng"):
        start = now - relativedelta(months=n)
    elif unit.startswith("quý"):
        start = now - relativedelta(months=3*n)
    else:
        start = now - relativedelta(years=n)

    return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")

DEFAULT_PRICE_SOURCE = "VCI"
DEFAULT_COMPANY_SOURCE = "TCBS"
MAX_WORKERS = 5

def convert_datetime_vectorized(data: List[Dict]) -> List[Dict]:
    if not data:
        return data

    df = pd.DataFrame(data)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        elif df[col].dtype == 'object':
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if hasattr(sample, 'strftime'):
                df[col] = df[col].apply(
                    lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if hasattr(x, 'hour')
                    else x.strftime("%Y-%m-%d") if hasattr(x, 'strftime') else x
                )

    return df.to_dict(orient="records")

class VNStockService:
    def __init__(self, price_source: str = DEFAULT_PRICE_SOURCE):
        self.price_source = price_source

    def company_overview(self, symbol: str) -> pd.DataFrame:
        trace.add_api_call("company_overview", {"symbol": symbol}, f"Lấy thông tin công ty {symbol}")
        return Company(symbol=symbol, source=DEFAULT_COMPANY_SOURCE).overview()

    def company_shareholders(self, symbol: str) -> pd.DataFrame:
        trace.add_api_call("company_shareholders", {"symbol": symbol}, f"Lấy danh sách cổ đông {symbol}")
        return Company(symbol=symbol, source=DEFAULT_COMPANY_SOURCE).shareholders()

    def company_officers(self, symbol: str, filter_by: str = "working") -> pd.DataFrame:
        trace.add_api_call("company_officers", {"symbol": symbol, "filter_by": filter_by}, f"Lấy ban lãnh đạo {symbol}")
        return Company(symbol=symbol, source=DEFAULT_COMPANY_SOURCE).officers(filter_by=filter_by)

    def company_subsidiaries(self, symbol: str) -> pd.DataFrame:
        trace.add_api_call("company_subsidiaries", {"symbol": symbol}, f"Lấy công ty con {symbol}")
        return Company(symbol=symbol, source=DEFAULT_COMPANY_SOURCE).subsidiaries()

    @lru_cache(maxsize=128)
    def _history_cached(self, symbol: str, start: str, end: str, interval: str = "1D") -> str:
        q = Quote(symbol=symbol, source=self.price_source)
        df = q.history(start=start, end=end, interval=interval)
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
        return df.to_json(orient="records", date_format="iso")

    def history(self, symbol: str, start: str, end: str, interval: str = "1D") -> pd.DataFrame:
        trace.add_api_call("history", {"symbol": symbol, "start": start, "end": end, "interval": interval},
                          f"Lấy dữ liệu giá {symbol} từ {start} đến {end}")
        json_str = self._history_cached(symbol, start, end, interval)
        df = pd.read_json(StringIO(json_str), orient="records")
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
        return df

    def history_parallel(self, symbols: List[str], start: str, end: str, interval: str = "1D") -> pd.DataFrame:
        def fetch_one(sym):
            df = self.history(sym, start, end, interval)
            df["symbol"] = sym
            return df

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_one, sym): sym for sym in symbols}
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Lỗi fetch {futures[future]}: {e}")

        return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

class Agent:
    def __init__(self, llm_provider: str = "gemini"):
        """
        Initialize Agent

        Args:
            llm_provider: LLM provider name ("gemini", "openai", "claude")
        """
        self.svc = VNStockService()

        # Initialize LLM Agent (tự đọc API key từ env)
        try:
            self.llm_agent = LLMAgent(provider=llm_provider)
        except Exception as e:
            print(f"Warning: Không thể khởi tạo LLM Agent: {e}")
            self.llm_agent = None

    def handle(self, question: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Xử lý câu hỏi

        Args:
            question: Câu hỏi tiếng Việt
            use_llm: Có dùng LLM không (mặc định True)

        Returns:
            Dict với answer, data, meta
        """
        trace.set_question(question)

        if not use_llm or not self.llm_agent or not self.llm_agent.is_ready():
            return {"answer": "LLM chưa được cấu hình."}

        try:
            action_info = self._analyze_question(question)
            trace.set_analysis(action_info)

            if not action_info or "error" in action_info:
                return {"answer": "Không hiểu câu hỏi. Vui lòng thử lại."}

            data = self._fetch_data(action_info)

            if "error" in data:
                return {"answer": data["error"]}

            trace.set_data_summary({"type": data.get("type"), "rows": len(data.get("raw_data", []))})

            raw_answer = self._generate_answer(question, action_info, data)

            answer = format_answer_with_table(
                raw_answer, data.get("raw_data", []),
                {"action": action_info.get("action"), "symbols": action_info.get("symbols", [])}
            )
            trace.set_answer(answer)
            trace.save()

            raw_data = data.get("raw_data")
            if isinstance(raw_data, list) and raw_data:
                raw_data = convert_datetime_vectorized(raw_data)

            return {
                "answer": answer,
                "data": raw_data,
                "meta": {
                    "action": action_info.get("action"),
                    "symbols": action_info.get("symbols", []),
                    "start": action_info.get("start"),
                    "end": action_info.get("end")
                }
            }

        except Exception as e:
            return {"answer": f"Lỗi xử lý: {str(e)}"}

    def _analyze_question(self, question: str) -> Dict[str, Any]:
        prompt = f"""Phân tích câu hỏi về chứng khoán và trả về JSON:

Câu hỏi: "{question}"

CÁC LOẠI ACTION:
- "price_history": Lấy lịch sử giá OHLCV đầy đủ
- "shareholders": Cổ đông lớn
- "officers": Ban lãnh đạo
- "subsidiaries": Công ty con
- "company_info": Thông tin công ty
- "rsi": Tính RSI
- "sma": Tính SMA
- "compare": So sánh GIÁ/OHLCV nhiều mã (hiển thị đầy đủ open, high, low, close, volume)
- "aggregate": Khi câu hỏi CHỈ QUAN TÂM một vài trường cụ thể (VD: chỉ volume, chỉ giá đóng cửa)
  Dấu hiệu: "so sánh volume", "tổng volume", "khối lượng giao dịch", "giá trung bình"

QUAN TRỌNG:
- Nếu câu hỏi có "so sánh volume" hoặc "so sánh khối lượng" → dùng "compare" + display_fields
- Nếu câu hỏi có "tổng", "trung bình", "min", "max" → dùng "aggregate"

TRÍCH XUẤT:
- symbols: Mã CK (VD: ["VCB"], ["VIC", "HPG"])
- time_phrase: "10 ngày", "2 tuần", "1 tháng"
- interval: "1D" (mặc định)
- windows: [9, 20] cho "SMA9 và SMA20", [14] cho "RSI14"
- display_fields: Danh sách trường cần hiển thị (cho "compare" hoặc "aggregate")
  VD "so sánh volume": ["time", "symbol", "volume"]
  VD "volume và giá": ["time", "symbol", "volume", "close"]
  VD "giá đóng cửa": ["time", "close"]
  Luôn bao gồm "time", thêm "symbol" nếu có nhiều mã

CHỈ trả JSON, KHÔNG giải thích."""

        try:
            text = self.llm_agent.generate(prompt)

            if text.startswith("```"):
                text = re.sub(r"```(?:json)?\n?", "", text).strip()

            result = json.loads(text)

            if "time_phrase" in result and result["time_phrase"]:
                start, end = compute_range_from_phrase(result["time_phrase"])
                result["start"] = start
                result["end"] = end

            return result

        except Exception as e:
            return {"error": str(e)}

    def _fetch_data(self, action_info: Dict[str, Any]) -> Dict[str, Any]:
        action = action_info.get("action")
        symbols = action_info.get("symbols", [])

        if not symbols:
            return {"error": "Không xác định được mã chứng khoán"}

        symbol = symbols[0]

        try:
            if action == "company_info":
                df = self.svc.company_overview(symbol)
                return {"type": "company_info", "raw_data": df.to_dict(orient="records")}

            elif action == "shareholders":
                df = self.svc.company_shareholders(symbol)
                return {"type": "shareholders", "raw_data": df.to_dict(orient="records")}

            elif action == "officers":
                df = self.svc.company_officers(symbol)
                return {"type": "officers", "raw_data": df.to_dict(orient="records")}

            elif action == "subsidiaries":
                df = self.svc.company_subsidiaries(symbol)
                return {"type": "subsidiaries", "raw_data": df.to_dict(orient="records")}

            elif action in ["price_history", "rsi", "sma", "compare", "aggregate"]:
                start = action_info.get("start")
                end = action_info.get("end")
                interval = action_info.get("interval", "1D")

                if not start or not end:
                    start, end = compute_range_from_phrase("30 ngày")

                if len(symbols) > 1:
                    df = self.svc.history_parallel(symbols, start, end, interval)
                else:
                    df = self.svc.history(symbol, start, end, interval)

                if action == "rsi":
                    windows = action_info.get("windows", [14])
                    if not isinstance(windows, list):
                        windows = [windows] if windows else [14]
                    df["RSI"] = rsi(df["close"], windows[0])
                    return {"type": "rsi", "raw_data": df.to_dict(orient="records")}

                elif action == "sma":
                    windows = action_info.get("windows", [20])
                    if not isinstance(windows, list):
                        windows = [windows] if windows else [20]
                    for w in windows:
                        df[f"SMA{w}"] = sma(df["close"], w)
                    return {"type": "sma", "raw_data": df.to_dict(orient="records")}

                elif action == "compare":
                    display_fields = action_info.get("display_fields", [])
                    if display_fields:
                        if "time" in df.columns and "time" not in display_fields:
                            display_fields = ["time"] + display_fields
                        if "symbol" in df.columns and len(symbols) > 1 and "symbol" not in display_fields:
                            display_fields = ["symbol"] + display_fields
                        available_fields = [f for f in display_fields if f in df.columns]
                        if available_fields:
                            df = df[available_fields].copy()
                    return {"type": "compare", "raw_data": df.to_dict(orient="records")}

                elif action == "aggregate":
                    display_fields = action_info.get("display_fields", [])
                    if "time" in df.columns and "time" not in display_fields:
                        display_fields = ["time"] + display_fields
                    if display_fields:
                        available_fields = [f for f in display_fields if f in df.columns]
                        if available_fields:
                            df = df[available_fields].copy()
                    return {"type": "aggregate", "raw_data": df.to_dict(orient="records")}

                else:
                    return {"type": "price_history", "raw_data": df.to_dict(orient="records")}

            else:
                return {"error": f"Action không hỗ trợ: {action}"}

        except Exception as e:
            return {"error": f"Lỗi lấy dữ liệu: {str(e)}"}

    def _generate_answer(self, question: str, action_info: Dict[str, Any], data: Dict[str, Any]) -> str:
        raw_data = data.get("raw_data", [])
        action = action_info.get("action")
        symbols = action_info.get("symbols", [])

        if len(raw_data) == 0:
            data_sample = "Không có dữ liệu"
        elif action == "compare" and len(symbols) > 1:
            df_full = pd.DataFrame(raw_data)
            data_sample = df_full.to_string(index=False)
            data_sample += f"\n\nTổng: {len(raw_data)} dòng từ {len(symbols)} mã ({', '.join(symbols)})"
        elif len(raw_data) <= 20:
            data_sample = pd.DataFrame(raw_data).to_string(index=False)
        else:
            df_sample = pd.DataFrame(raw_data)
            head_tail = pd.concat([df_sample.head(5), df_sample.tail(5)])
            data_sample = head_tail.to_string(index=False)
            data_sample = f"=== MẪU (5 đầu + 5 cuối) ===\n{data_sample}\n\nTổng: {len(raw_data)} dòng"

        prompt = f"""Trả lời câu hỏi dựa trên dữ liệu cổ phiếu Việt Nam:

Câu hỏi: "{question}"

Dữ liệu:
{data_sample}

Yêu cầu: Nêu số liệu quan trọng và ngôn ngữ tự nhiên

Trả lời:"""

        try:
            return self.llm_agent.generate(prompt)
        except Exception as e:
            return f"Lỗi: {str(e)}"

class AskRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi tiếng Việt")
    use_llm: Optional[bool] = True

class AskResponse(BaseModel):
    answer: str
    data: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None

app = FastAPI(title="VNStock Agent")
_agent = Agent()
_svc = VNStockService()

@app.get("/health")
async def health():
    llm_ready = _agent.llm_agent and _agent.llm_agent.is_ready()
    llm_info = _agent.llm_agent.info() if _agent.llm_agent else {}
    return {
        "status": "ok",
        "llm_ready": llm_ready,
        "llm_info": llm_info
    }

@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    out = _agent.handle(req.question, use_llm=bool(req.use_llm))
    if "answer" not in out:
        out["answer"] = "Xin lỗi, không tạo được câu trả lời."
    if "data" in out and isinstance(out["data"], list) and out["data"]:
        out["data"] = convert_datetime_vectorized(out["data"])
    return JSONResponse(content=out)

@app.get("/price/history")
async def price_history(symbol: str, start: str, end: str, interval: str = "1D"):
    df = _svc.history(symbol, start, end, interval=interval)
    data = convert_datetime_vectorized(df.to_dict(orient="records"))
    return {"symbol": symbol, "start": start, "end": end, "interval": interval, "data": data}
