from app.services.messages import ai_message, template_message


def _summary():
    return {
        "average_pm25": 42.5,
        "peak_pm25": 53,
        "best_window": None,
        "worst_window": None,
    }


class FakeBedrock:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.request = None

    def converse(self, **request):
        self.request = request
        if self.error:
            raise self.error
        return {"output": {"message": {"content": [{"text": self.text}]}}}


def _fallback():
    return template_message(
        "Sample School",
        "YELLOW",
        42.5,
        53,
        None,
        None,
        language="English",
        advice="Review outdoor activities.",
    )


def test_bedrock_message_uses_known_facts_and_includes_status_and_disclaimer():
    client = FakeBedrock(
        "YELLOW: Sample School should review outdoor activities. Informational only, not medical advice."
    )
    result = ai_message(
        "Sample School",
        "YELLOW",
        "Review outdoor activities.",
        _summary(),
        "English",
        "model-id",
        bedrock_client=client,
    )
    assert result == client.text
    assert client.request["modelId"] == "model-id"
    assert "no medical claims" in client.request["messages"][0]["content"][0]["text"]


def test_bedrock_exception_uses_template_fallback():
    assert ai_message(
        "Sample School", "YELLOW", "Review outdoor activities.", _summary(), "English",
        "model-id", bedrock_client=FakeBedrock(error=RuntimeError("private")),
    ) == _fallback()


def test_bedrock_reply_without_status_uses_template_fallback():
    assert ai_message(
        "Sample School", "YELLOW", "Review outdoor activities.", _summary(), "English",
        "model-id", bedrock_client=FakeBedrock("Air conditions need attention."),
    ) == _fallback()


def test_empty_model_id_skips_bedrock_and_uses_template():
    client = FakeBedrock("should not be called")
    result = ai_message(
        "Sample School", "YELLOW", "Review outdoor activities.", _summary(), "English",
        "", bedrock_client=client,
    )
    assert result == _fallback()
    assert client.request is None


def test_overlong_bedrock_reply_uses_template_fallback():
    long_reply = "YELLOW " + "word " * 65 + "Informational only, not medical advice."
    assert ai_message(
        "Sample School", "YELLOW", "Review outdoor activities.", _summary(), "English",
        "model-id", bedrock_client=FakeBedrock(long_reply),
    ) == _fallback()
