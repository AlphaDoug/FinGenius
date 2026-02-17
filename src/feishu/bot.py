"""
飞书机器人核心模块
支持两种模式：
1. Webhook 模式：仅发送消息（群自定义机器人）
2. App 模式：接收+发送消息（企业应用机器人，支持事件订阅）
"""

import asyncio
import hashlib
import base64
import hmac
import json
import re
import time
from typing import Any, Dict, Optional

import requests
from src.logger import logger


# Agent 名称映射
AGENT_NAME_MAP = {
    "sentiment_agent": "市场情绪分析师",
    "risk_control_agent": "风险控制专家",
    "hot_money_agent": "游资分析师",
    "technical_analysis_agent": "技术分析师",
    "chip_analysis_agent": "筹码分析师",
    "big_deal_analysis_agent": "大单分析师",
    "report_agent": "报告生成专家",
    "System": "系统",
}


def get_agent_display_name(agent_id: str) -> str:
    return AGENT_NAME_MAP.get(agent_id, agent_id)


class FeishuWebhookBot:
    """飞书群自定义机器人（Webhook 模式，仅发送）"""

    def __init__(self, webhook_url: str, secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret

    def _gen_sign(self) -> tuple[str, str]:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return timestamp, sign

    def send(self, payload: dict) -> dict:
        if self.secret:
            ts, sign = self._gen_sign()
            payload["timestamp"] = ts
            payload["sign"] = sign

        headers = {"Content-Type": "application/json; charset=utf-8"}
        resp = requests.post(
            self.webhook_url, headers=headers, data=json.dumps(payload), timeout=10
        )
        result = resp.json()
        if result.get("code") != 0:
            logger.error(f"飞书消息发送失败: {result}")
        return result

    def send_text(self, text: str) -> dict:
        return self.send({"msg_type": "text", "content": {"text": text}})

    def send_interactive(self, card: dict) -> dict:
        return self.send({"msg_type": "interactive", "card": card})


class FeishuAppBot:
    """
    飞书企业应用机器人（App 模式，支持收发消息）
    使用长连接（WebSocket）接收事件，无需公网地址。
    """

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token = ""
        self._token_expire_time = 0

    def _get_tenant_access_token(self) -> str:
        if time.time() < self._token_expire_time and self._tenant_access_token:
            return self._tenant_access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(
            url,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取 tenant_access_token 失败: {data}")
        self._tenant_access_token = data["tenant_access_token"]
        self._token_expire_time = time.time() + data.get("expire", 7200) - 300
        return self._tenant_access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_tenant_access_token()}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def send_message(self, receive_id: str, msg_type: str, content: str,
                     receive_id_type: str = "chat_id") -> dict:
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content,
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=15)
        result = resp.json()
        if result.get("code") != 0:
            logger.error(f"飞书消息发送失败: {result}")
        return result

    def send_text(self, chat_id: str, text: str) -> dict:
        content = json.dumps({"text": text})
        return self.send_message(chat_id, "text", content)

    def send_interactive(self, chat_id: str, card: dict) -> dict:
        content = json.dumps(card)
        return self.send_message(chat_id, "interactive", content)

    def reply_message(self, message_id: str, msg_type: str, content: str) -> dict:
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
        payload = {"msg_type": msg_type, "content": content}
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=15)
        result = resp.json()
        if result.get("code") != 0:
            logger.error(f"飞书回复消息失败: {result}")
        return result

    def reply_interactive(self, message_id: str, card: dict) -> dict:
        content = json.dumps(card)
        return self.reply_message(message_id, "interactive", content)


def parse_stock_code(text: str) -> Optional[str]:
    """从用户消息中解析股票代码"""
    text = text.strip()
    # 纯数字 6 位
    m = re.search(r"\b(\d{6})\b", text)
    if m:
        return m.group(1)
    return None
