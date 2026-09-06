from __future__ import annotations

import ast
import base64
import enum
import json
import re
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


class ParseError(ValueError):
    """Raised when model output cannot be parsed into structured objects."""


# 用途：
# - 将 Python literal fallback 产生的 bytes-like 值归一化为 JSON-safe factory，避免后续阶段再各自修补
# 输入：
# - value: 解析后的任意 Python 值，可能包含 bytes/bytearray/memoryview、dict、list、tuple
# 输出：
# - 只包含 JSON-safe 结构的值；bytes-like 会转成统一的 bytes factory
def normalize_python_literal_json_value(value: Any) -> Any:
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes):
        return {
            "__factory__": "bytes",
            "encoding": "base64",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, list):
        return [normalize_python_literal_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_python_literal_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: normalize_python_literal_json_value(item)
            for key, item in value.items()
        }
    return value


# 用途：
# - 去掉模型回复外层 fenced code block，便于后续统一 JSON 抽取和解析
# 输入：
# - text: 模型原始文本回复
# 输出：
# - 去掉外层 fence 后的正文文本
def strip_fenced_code_block(text: str) -> str:
    stripped = str(text or "").strip()
    fence_match = re.match(r"^```[^\n\r]*[\n\r]+", stripped)
    if fence_match:
        stripped = stripped[fence_match.end() :].lstrip()
    elif stripped.startswith("```"):
        stripped = stripped[len("```") :].lstrip()
    if stripped.endswith("```"):
        stripped = stripped[: -len("```")].rstrip()
    return stripped


# 用途：
# - 从模型回复中提取第一段完整 JSON value，统一处理说明文字、fence 和字符串内括号
# 输入：
# - text: 模型原始文本回复
# 输出：
# - 第一段完整 JSON value 文本；无法提取时抛 ParseError
def extract_json_value_text(text: str) -> str:
    stripped = strip_fenced_code_block(text)
    object_start = stripped.find("{")
    list_start = stripped.find("[")
    start_candidates = [index for index in (object_start, list_start) if index != -1]
    if not start_candidates:
        raise ParseError(f"Invalid JSON response: {str(text or '')[:300]}")
    start_index = min(start_candidates)
    opening_char = stripped[start_index]
    closing_char = "}" if opening_char == "{" else "]"

    depth = 0
    in_string = False
    string_quote = ""
    escaped = False
    for index in range(start_index, len(stripped)):
        char = stripped[index]
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == string_quote:
                in_string = False
                string_quote = ""
            continue
        if char in {'"', "'"}:
            in_string = True
            string_quote = char
            continue
        if char == opening_char:
            depth += 1
            continue
        if char == closing_char:
            depth -= 1
            if depth == 0:
                return stripped[start_index : index + 1].strip()
    raise ParseError(f"Invalid JSON response (extracted failed): {str(text or '')[:300]}")


# 用途：
# - 从模型回复中提取第一段完整 JSON object，供要求 object 顶层结构的调用方复用
# 输入：
# - text: 模型原始文本回复
# 输出：
# - 第一段完整 JSON object 文本；若顶层不是 object 则抛 ParseError
def extract_json_object_text(text: str) -> str:
    extracted = extract_json_value_text(text)
    if not extracted.startswith("{"):
        raise ParseError("Parsed response must be a JSON object.")
    return extracted


class ResponseParser:
    """Converts model output into typed runtime objects."""

    # 用途：
    # - 将模型输出解析为顶层 JSON object，并复用统一的 JSON value 容错解析链
    # 输入：
    # - content: 模型原始文本回复
    # 输出：
    # - 解析后的 JSON object；顶层不是 object 时抛 ParseError
    def parse_json(self, content: str) -> dict[str, Any]:
        data = self.parse_json_value(content)

        if not isinstance(data, dict):
            raise ParseError("Parsed response must be a JSON object.")
        return data

    # 用途：
    # - 解析模型输出中的任意顶层 JSON value，并统一处理提取、转义修复和 Python literal fallback
    # 输入：
    # - content: 模型原始文本回复
    # 输出：
    # - 解析后的 JSON-safe 值
    def parse_json_value(self, content: str) -> Any:
        normalized = self._normalize_model_json_text(content)
        try:
            data = json.loads(normalized)
        except json.JSONDecodeError:
            repaired_normalized = self._repair_common_json_text(normalized)
            try:
                data = json.loads(repaired_normalized)
            except json.JSONDecodeError:
                candidate_text = self._extract_outermost_json_candidate(repaired_normalized)
                try:
                    data = json.loads(candidate_text)
                except Exception as exc:
                    try:
                        data = self._parse_first_decodable_json_value(repaired_normalized)
                    except Exception:
                        extracted_source = candidate_text if candidate_text != repaired_normalized else normalized
                        extracted = extract_json_value_text(extracted_source)
                        repaired = self._repair_common_json_text(extracted)
                        try:
                            data = self._parse_pythonish_json(repaired)
                        except Exception:
                            raise ParseError(
                                f"Invalid JSON response (extracted failed): {content[:300]}"
                            ) from exc
        return normalize_python_literal_json_value(data)

    # 用途：
    # - 将 reviewer payload 等运行值转为稳定可展示字符串，避免 dict/list 展示顺序漂移
    # 输入：
    # - value: reviewer item 中的任意值
    # 输出：
    # - 适合写入文本报告的稳定字符串
    def _stringify_review_value(self, value: Any) -> str:
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value)

    # 用途：
    # - 统一修复模型常见 JSON 文本问题，优先处理括号失衡、trailing comma 和转义噪声
    # 输入：
    # - text: 已去 fence 的 JSON-ish 文本
    # 输出：
    # - 更接近合法 JSON / Python literal 的修复后文本
    def _repair_common_json_text(self, text: str) -> str:
        repaired = self._repair_common_json_escapes(text)
        repaired = self._escape_unescaped_quotes_inside_json_strings(repaired)
        repaired = self._repair_broken_identifier_keys(repaired)
        repaired = self._remove_value_terminating_semicolons(repaired)
        repaired = self._remove_trailing_commas(repaired)
        repaired = self._rebalance_json_brackets(repaired)
        return repaired

    # 用途：
    # - 在解析前清理模型响应中的非 JSON 包装和常见推理残片，降低 provider 输出噪声对解析的影响
    # 输入：
    # - content: 模型原始文本回复
    # 输出：
    # - 去 fence、去 think 标签、去首尾空白后的 JSON-ish 文本
    def _normalize_model_json_text(self, content: str) -> str:
        normalized = strip_fenced_code_block(content)
        normalized = re.sub(r"<think>.*?</think>", "", normalized, flags=re.DOTALL | re.IGNORECASE)
        normalized = re.sub(r"</?think>", "", normalized, flags=re.IGNORECASE)
        return normalized.strip()

    # 用途：
    # - 修复模型常见的错误转义，避免 json.loads 因无意义转义直接失败
    # 输入：
    # - text: 原始 JSON-ish 文本
    # 输出：
    # - 去除常见错误转义后的文本
    def _repair_common_json_escapes(self, text: str) -> str:
        return text.replace("\\'", "'")

    # 用途：
    # - 修复模型在 JSON 字符串内容中直接写双引号的常见错误，例如 markdown code span 中的 `"sample"`
    # 输入：
    # - text: 原始 JSON-ish 文本
    # 输出：
    # - 将看起来不像字符串结束符的内部双引号转义后的文本
    def _escape_unescaped_quotes_inside_json_strings(self, text: str) -> str:
        normalized = str(text or "")
        result: list[str] = []
        in_string = False
        escaped = False
        index = 0

        while index < len(normalized):
            char = normalized[index]
            if escaped:
                result.append(char)
                escaped = False
                index += 1
                continue

            if char == "\\" and in_string:
                result.append(char)
                escaped = True
                index += 1
                continue

            if char != '"':
                result.append(char)
                index += 1
                continue

            if not in_string:
                in_string = True
                result.append(char)
                index += 1
                continue

            if self._looks_like_json_string_close(normalized, index + 1):
                in_string = False
                result.append(char)
            else:
                result.append('\\"')
            index += 1

        return "".join(result)

    # 用途：
    # - 判断 JSON 字符串中的双引号是否像合法结束符，而不是内容里的未转义引号
    # 输入：
    # - text: 原始 JSON-ish 文本
    # - start_index: 双引号后一位
    # 输出：
    # - 若后续是 JSON key/value 分隔符、容器分隔符、闭合符或文本结束则返回 True
    def _looks_like_json_string_close(self, text: str, start_index: int) -> bool:
        index = start_index
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return True
        return text[index] in {":", ",", "}", "]"}

    # 用途：
    # - 修复模型偶发把 JSON key 的下划线或结尾引号打断的错误，例如 `"case"_name` 和 `"case_name"":`
    # 输入：
    # - text: 原始 JSON-ish 文本
    # 输出：
    # - 修复常见 key 断裂后的 JSON-ish 文本
    def _repair_broken_identifier_keys(self, text: str) -> str:
        repaired = re.sub(
            r'"([A-Za-z_][A-Za-z0-9_]*)"_([A-Za-z0-9_]+)"?\s*:',
            r'"\1_\2":',
            str(text or ""),
        )
        repaired = re.sub(
            r'"([A-Za-z_][A-Za-z0-9_]*)""\s*:',
            r'"\1":',
            repaired,
        )
        return repaired

    # 用途：
    # - 删除模型偶发写在 JSON value 之后的语句式分号，例如 `"field": "value";`
    # 输入：
    # - text: 原始 JSON-ish 文本
    # 输出：
    # - 仅移除字符串外、且后续紧跟 JSON 分隔符/闭合符的 value 终止分号后的文本
    def _remove_value_terminating_semicolons(self, text: str) -> str:
        result: list[str] = []
        in_string = False
        string_quote = ""
        escape = False
        index = 0
        normalized = str(text or "")
        while index < len(normalized):
            char = normalized[index]
            if in_string:
                result.append(char)
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == string_quote:
                    in_string = False
                    string_quote = ""
                index += 1
                continue
            if char in {'"', "'"}:
                in_string = True
                string_quote = char
                result.append(char)
                index += 1
                continue
            if char == ";":
                lookahead = index + 1
                while lookahead < len(normalized) and normalized[lookahead].isspace():
                    lookahead += 1
                if lookahead >= len(normalized) or normalized[lookahead] in {"}", "]", ","}:
                    index += 1
                    continue
            result.append(char)
            index += 1
        return "".join(result)

    # 用途：
    # - 从含有前置坏片段或解释文本的模型回复中扫描第一段可被 JSONDecoder 直接解析的 value
    # 输入：
    # - text: 已做基础修复的 JSON-ish 文本
    # 输出：
    # - 第一段可解析 JSON value；找不到时抛 ParseError
    def _parse_first_decodable_json_value(self, text: str) -> Any:
        decoder = json.JSONDecoder()
        normalized = str(text or "")
        for index, char in enumerate(normalized):
            if char not in {"{", "["}:
                continue
            try:
                value, _ = decoder.raw_decode(normalized[index:])
            except json.JSONDecodeError:
                continue
            return value
        raise ParseError(f"Invalid JSON response: {normalized[:300]}")

    # 用途：
    # - 从修复后的文本中截取最外层 JSON candidate，避免中途多余 closing bracket 导致提取过早结束
    # 输入：
    # - text: 已做基础修复的 JSON-ish 文本
    # 输出：
    # - 从首个 opening bracket 到最后一个同类 closing bracket 的 candidate 文本
    def _extract_outermost_json_candidate(self, text: str) -> str:
        stripped = str(text or "").strip()
        object_start = stripped.find("{")
        list_start = stripped.find("[")
        start_candidates = [index for index in (object_start, list_start) if index != -1]
        if not start_candidates:
            return stripped
        start_index = min(start_candidates)
        opening_char = stripped[start_index]
        closing_char = "}" if opening_char == "{" else "]"
        end_index = stripped.rfind(closing_char)
        if end_index < start_index:
            return stripped[start_index:]
        return stripped[start_index : end_index + 1]

    # 用途：
    # - 去掉 object/list 关闭符前的 trailing comma，兼容模型常见的多余逗号
    # 输入：
    # - text: 原始 JSON-ish 文本
    # 输出：
    # - 去掉 trailing comma 后的文本
    def _remove_trailing_commas(self, text: str) -> str:
        result: list[str] = []
        in_string = False
        string_quote = ""
        escape = False
        index = 0
        while index < len(text):
            char = text[index]
            if in_string:
                result.append(char)
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == string_quote:
                    in_string = False
                    string_quote = ""
                index += 1
                continue
            if char in {'"', "'"}:
                in_string = True
                string_quote = char
                result.append(char)
                index += 1
                continue
            if char == ",":
                lookahead = index + 1
                while lookahead < len(text) and text[lookahead].isspace():
                    lookahead += 1
                if lookahead < len(text) and text[lookahead] in {"}", "]"}:
                    index += 1
                    continue
            result.append(char)
            index += 1
        return "".join(result)

    # 用途：
    # - 修复模型输出中多余或缺失的 JSON 括号，优先消除未匹配 closing bracket 并补齐尾部 opening bracket
    # 输入：
    # - text: 原始 JSON-ish 文本
    # 输出：
    # - 括号尽量平衡后的文本
    def _rebalance_json_brackets(self, text: str) -> str:
        opener_for_closer = {"}": "{", "]": "["}
        closer_for_opener = {"{": "}", "[": "]"}
        repaired: list[str] = []
        stack: list[str] = []
        in_string = False
        string_quote = ""
        escape = False

        for index, char in enumerate(text):
            if in_string:
                repaired.append(char)
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == string_quote:
                    in_string = False
                    string_quote = ""
                continue
            if char in {'"', "'"}:
                in_string = True
                string_quote = char
                repaired.append(char)
                continue
            if char in closer_for_opener:
                stack.append(char)
                repaired.append(char)
                continue
            if char in opener_for_closer:
                expected_opener = opener_for_closer[char]
                if stack and stack[-1] == expected_opener:
                    if (
                        char == "}"
                        and len(stack) == 1
                        and self._looks_like_more_object_members(text, index + 1)
                    ):
                        continue
                    stack.pop()
                    repaired.append(char)
                continue
            repaired.append(char)

        while stack:
            repaired.append(closer_for_opener[stack.pop()])
        return "".join(repaired)

    # 用途：
    # - 判断某个顶层 object 关闭符后面是否还像是未完成的成员声明，避免多余 `}` 让提取逻辑过早截断
    # 输入：
    # - text: 原始 JSON-ish 文本
    # - start_index: 当前 closing brace 后的起始位置
    # 输出：
    # - 若后续仍像 `, "next_key": ...` 这样的 object 成员则返回 True
    def _looks_like_more_object_members(self, text: str, start_index: int) -> bool:
        index = start_index
        while index < len(text) and text[index].isspace():
            index += 1
        while index < len(text) and text[index] == "}":
            index += 1
            while index < len(text) and text[index].isspace():
                index += 1
        while index < len(text) and text[index] == ",":
            index += 1
            while index < len(text) and text[index].isspace():
                index += 1
        if index >= len(text):
            return False
        return text[index] in {'"', "'"}

    # 用途：
    # - 将 Python-ish JSON 解析为 Python 值，兼容 true/false/null 和 bytes literal
    # 输入：
    # - text: 已做基础清洗的 Python-ish JSON 文本
    # 输出：
    # - `ast.literal_eval` 解析后的 Python 值
    def _parse_pythonish_json(self, text: str) -> Any:
        pythonized = self._replace_json_keywords_for_python_literals(text)
        return ast.literal_eval(pythonized)

    # 用途：
    # - 仅在字符串外替换 JSON 关键字，避免把普通文本内容误改成 Python 常量
    # 输入：
    # - text: 原始 JSON-ish 文本
    # 输出：
    # - 替换后的 Python literal 文本
    def _replace_json_keywords_for_python_literals(self, text: str) -> str:
        replacements = {
            "true": "True",
            "false": "False",
            "null": "None",
        }
        result: list[str] = []
        token: list[str] = []
        in_string = False
        string_quote = ""
        escape = False

        def flush_token() -> None:
            nonlocal token
            if not token:
                return
            word = "".join(token)
            result.append(replacements.get(word, word))
            token = []

        for char in text:
            if in_string:
                result.append(char)
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == string_quote:
                    in_string = False
                    string_quote = ""
                continue

            if char in {'"', "'"}:
                flush_token()
                in_string = True
                string_quote = char
                result.append(char)
                continue

            if char.isalpha():
                token.append(char)
                continue

            flush_token()
            result.append(char)

        flush_token()
        return "".join(result)

    # 用途：
    # - 将运行期对象递归转换为 JSON-safe 值，供日志、报告和 prompt 材料落盘
    # 输入：
    # - value: 任意运行期值，可能包含 dataclass、Decimal、Enum、Path、dict/list/tuple/set
    # 输出：
    # - 可被 json.dumps 稳定序列化的值
    def to_serializable(self, value: Any) -> Any:
        if is_dataclass(value):
            return self.to_serializable(asdict(value))
        if isinstance(value, enum.Enum):
            return self.to_serializable(value.value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, BaseException):
            return str(value)
        if isinstance(value, dict):
            return {k: self.to_serializable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.to_serializable(v) for v in value]
        if isinstance(value, (set, frozenset)):
            normalized_items = [self.to_serializable(v) for v in value]
            return sorted(
                normalized_items,
                key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str),
            )
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if hasattr(value, "__dict__"):
            return self.to_serializable(vars(value))
        return str(value)


_DEFAULT_RESPONSE_PARSER = ResponseParser()


# 用途：
# - 为项目各处提供统一的 JSON object 文本解析入口，收口 fenced block、JSON 提取和 Python literal 修复
# 输入：
# - text: 模型或审计文件中的原始 JSON 文本
# 输出：
# - 解析后的 JSON object；失败时抛 ParseError
def parse_json_object_text(text: str) -> dict[str, Any]:
    return _DEFAULT_RESPONSE_PARSER.parse_json(text)
