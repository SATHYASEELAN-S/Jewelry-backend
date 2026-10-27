from rest_framework.renderers import JSONRenderer


class CustomJSONRenderer(JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context["response"].status_code

        if not str(status_code).startswith("2"):
            return super().render(data, accepted_media_type, renderer_context)

        message = "Request successful."

        if isinstance(data, dict) and "message" in data:
            message = data["message"]
            data = {k: v for k, v in data.items() if k != "message"}

        return super().render(
            {
                "success": True,
                "status_code": status_code,
                "message": message,
                "data": data,
            },
            accepted_media_type,
            renderer_context,
        )
