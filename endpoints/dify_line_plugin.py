"""このモジュールではLINE Webhookを受信するエンドポイントを定義します"""

from typing import Mapping, cast
from werkzeug import Request, Response
from dify_plugin import Endpoint  # type: ignore
from linebot.v3 import WebhookHandler  # type: ignore
from linebot.v3.messaging import (  # type: ignore
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (  # type: ignore
    Configuration,
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.exceptions import InvalidSignatureError  # type: ignore


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
        access_token = settings["line_channel_access_token"]
        configuration = Configuration(access_token=access_token)
        handler = WebhookHandler(settings["line_channel_secret"])

        @handler.add(MessageEvent, message=TextMessageContent)
        def handle_text_event(text_event: MessageEvent):
            event_dict = text_event.to_dict()
            if self._should_respond(event_dict):
                self._process_text_message_event_to_linebot(
                    text_event, configuration, app_id
                )

        signature = r.headers["X-Line-Signature"]
        body = r.get_data(as_text=True)

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            pass

        return Response("", status=200, content_type="application/json")

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
        self, event: MessageEvent, configuration: Configuration, app_id: str
    ):
        # Difyワークフローの呼び出し
        text = cast(TextMessageContent, event.message).text
        response = self.session.app.workflow.invoke(
            app_id=app_id,
            inputs={"messageText": text},
            response_mode="blocking",
        )

        data = response["data"]
        if data["error"] is None:
            pass
        else:
            pass

        outputs = data["outputs"]
        output = outputs.get("output", "")
        if output != "":
            req = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=output)],
            )
            with ApiClient(configuration) as api_client:
                try:
                    mapi = MessagingApi(api_client)
                    mapi.reply_message(req)
                except Exception as e:  # pylint: disable=W0718
                    # Exception : module 'linebot.v3.webhooks.models' has no
                    # attribute 'ReplyMessageResponse'
                    print(f"Exception : {e}")
