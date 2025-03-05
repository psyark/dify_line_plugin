""" このモジュールではLINE Webhookを受信するエンドポイントを定義します """

import json
from typing import Mapping
from werkzeug import Request, Response
from dify_plugin import Endpoint  # type: ignore


class DifyLinePluginEndpoint(Endpoint):
    """LINE Webhookを受信するエンドポイント"""

    def _invoke(
        self, r: Request, values: Mapping, settings: Mapping
    ) -> Response:
        """
        Invokes the endpoint with the given request.
        """
        app_id = settings["app_to_invoke"]["app_id"]
        
        def generator():
            response = self.session.app.workflow.invoke(
                app_id=app_id, inputs={}, response_mode="blocking"
            )
            yield json.dumps(response)
            
        return Response(
            generator(), status=200, content_type="application/json"
        )
