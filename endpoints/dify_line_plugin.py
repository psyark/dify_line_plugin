""" このモジュールではLINE Webhookを受信するエンドポイントを定義します """

import json
import base64
import hashlib
import hmac
from typing import Mapping

import requests
from werkzeug import Request, Response
from dify_plugin import Endpoint  # type: ignore


class DifyLinePluginEndpoint(Endpoint):  # pylint: disable=R0903
    """
    LINE Webhookを受信するエンドポイント
    https://developers.line.biz/ja/docs/messaging-api/receiving-messages/
    https://chat-suke-bescrnneaq-an.a.run.app
    """

    def _invoke(
        self, r: Request, values: Mapping, settings: Mapping
    ) -> Response:
        """Invokes the endpoint with the given request."""

        app_id = settings["app_to_invoke"]["app_id"]

        # 署名が検証できた場合だけLINE Webhookとして応答する
        if self._verify_signature(r, settings["line_channel_secret"]):
            body = r.get_json()

            for event in body.get("events", []):
                self._process_event(
                    event, settings["line_channel_access_token"], app_id
                )

        return Response("", status=200, content_type="application/json")

    def _process_event(self, event, channel_access_token: str, app_id: str):
        if event["type"] == "message":
            self._process_message_event(event, channel_access_token, app_id)

    def _process_message_event(
        self, event, channel_access_token: str, app_id: str
    ):
        if event["message"]["type"] == "text":
            self._process_text_message_event(
                event, channel_access_token, app_id
            )

    def _process_text_message_event(
        self, event, channel_access_token: str, app_id: str
    ):
        if self._should_respond(event):  # 返事をすべきテキストメッセージ
            self._process_text_message_event_to_linebot(
                event, channel_access_token, app_id
            )

    def _should_respond(self, event) -> bool:
        if event["source"]["type"] == "user":  # 1対1トーク
            return True

        mention = event["message"].get("mention", None)
        if mention is None:  # メンションがない
            return False

        for mentionees in mention["mentionees"]:
            if mentionees.get("isSelf", None):  # 自分宛てのメンションがある
                return True

        return False  # メンションはあるが自分宛てではない

    def _process_text_message_event_to_linebot(
        self, event, channel_access_token: str, app_id: str
    ):
        # Difyワークフローの呼び出し
        response = self.session.app.workflow.invoke(
            response_mode="blocking",
            app_id=app_id,
            inputs={"messageText": event["message"]["text"]},
        )
        data = response["data"]
        if data["error"] is None:
            pass
        else:
            pass

        outputs = data["outputs"]
        output = outputs.get("output", [])

        # 返信メッセージの作成
        reply_message = {
            "replyToken": event["replyToken"],
            "messages": [{"type": "text", "text": output}],
        }

        # LINE Messaging APIに返信メッセージを送信
        response = requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {channel_access_token}",
            },
            data=json.dumps(reply_message),
            timeout=10,
        )

        if response.status_code != 200:
            print("🚨", response)

    def _verify_signature(self, r: Request, channel_secret: str) -> bool:
        """署名の検証"""
        body = r.get_data(as_text=True)
        b64hash = hmac.new(
            channel_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = base64.b64encode(b64hash).decode("utf-8")
        return signature == r.headers.get("X-Line-Signature")
