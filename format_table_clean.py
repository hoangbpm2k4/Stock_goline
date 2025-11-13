#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
from typing import List, Dict, Any, Optional

def format_number(value: Any, is_volume: bool = False, is_price: bool = False) -> str:
    if pd.isna(value) or value == "" or value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return "N/A"
        if is_price:
            value = value * 1000
        if is_volume and abs(value) >= 1_000_000:
            if abs(value) >= 1_000_000_000:
                return f"{value/1_000_000_000:.1f}B"
            else:
                return f"{value/1_000_000:.1f}M"
        if abs(value - round(value)) < 0.0001:
            return f"{int(round(value)):,}"
        else:
            return f"{value:,.2f}"
    return str(value)


def detect_column_type(col_name: str) -> str:
    col_lower = col_name.lower()
    if 'time' in col_lower or 'date' in col_lower or 'ngày' in col_lower:
        return 'date'
    if 'volume' in col_lower or 'khối lượng' in col_lower:
        return 'volume'
    if any(x in col_lower for x in ['open', 'high', 'low', 'close', 'sma', 'rsi', 'giá', 'price', 'mở', 'cao', 'thấp', 'đóng']):
        return 'price'
    if 'percent' in col_lower or '%' in col_lower or 'tỷ lệ' in col_lower:
        return 'percent'
    return 'normal'


def format_table(data: List[Dict[str, Any]],
                 max_rows: Optional[int] = None,
                 style: str = 'compact') -> str:
    if not data or len(data) == 0:
        return "Không có dữ liệu"

    df = pd.DataFrame(data)
    columns = list(df.columns)

    if style == 'compact':
        priority_cols = []

        if 'symbol' in columns:
            priority_cols.append('symbol')

        for col in columns:
            if detect_column_type(col) == 'date':
                priority_cols.append(col)
                break

        has_ohlc = all(any(x in col.lower() for col in columns) for x in ['open', 'high', 'low', 'close'])

        if has_ohlc:
            for price_col in ['open', 'high', 'low', 'close']:
                for col in columns:
                    if price_col in col.lower():
                        priority_cols.append(col)
                        break
        else:
            for col in columns:
                if 'close' in col.lower() or 'đóng' in col.lower():
                    priority_cols.append(col)
                    break

        for col in columns:
            if detect_column_type(col) == 'volume':
                priority_cols.append(col)
                break

        for col in columns:
            if any(x in col.upper() for x in ['SMA', 'RSI', 'MACD']):
                priority_cols.append(col)

        if len(priority_cols) <= 1:
            priority_cols = columns

        df = df[priority_cols]
        columns = priority_cols

    if max_rows and len(df) > max_rows:
        if style == 'head_tail':
            head_count = max_rows // 2
            tail_count = max_rows - head_count
            df = pd.concat([df.head(head_count), df.tail(tail_count)])
        else:
            df = df.tail(max_rows)

    formatted_rows = [columns]

    for _, row in df.iterrows():
        formatted_row = []
        for col in columns:
            col_type = detect_column_type(col)
            value = row[col]
            if col_type == 'volume':
                formatted_row.append(format_number(value, is_volume=True))
            elif col_type == 'price':
                formatted_row.append(format_number(value, is_price=True))
            else:
                formatted_row.append(format_number(value))
        formatted_rows.append(formatted_row)

    col_widths = []
    for i, col in enumerate(columns):
        max_width = len(str(col))
        for row in formatted_rows[1:]:
            max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width)

    lines = []
    for row_idx, row in enumerate(formatted_rows):
        line_parts = []
        for col_idx, cell in enumerate(row):
            cell_str = str(cell)

            if any(c.isdigit() for c in cell_str):
                line_parts.append(cell_str.rjust(col_widths[col_idx]))
            else:
                line_parts.append(cell_str.ljust(col_widths[col_idx]))

        lines.append("  ".join(line_parts))

        if row_idx == 0:
            separator = "  ".join(["-" * w for w in col_widths])
            lines.append(separator)

    return "\n".join(lines)


def format_answer_with_table(answer: str, data: List[Dict[str, Any]], meta: Dict[str, Any]) -> str:
    if not data:
        return answer

    num_rows = len(data)
    table = format_table(data, max_rows=None, style='compact')

    result = [
        f"Tổng số dòng: {num_rows}",
        "",
        f"=== TẤT CẢ DỮ LIỆU ({num_rows} DÒNG) ===",
        table,
        ""
    ]

    if answer and len(answer) > 50:
        result.extend(["=== PHÂN TÍCH ===", answer])

    return "\n".join(result)
