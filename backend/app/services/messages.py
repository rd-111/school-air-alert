"""Plain, fact-based school alert messages in supported project languages."""

import json
from datetime import datetime

import boto3
from botocore.config import Config

DISCLAIMER = "Informational only, not medical advice."

_TEXT = {
    "English": {
        "average": "Average PM2.5 during school hours",
        "peak": "peak",
        "best": "Best time for outdoor activity",
        "avoid": "Avoid outdoors",
        "unavailable": "Unavailable",
        "sensitive": "Sensitive-student notice: consider indoor options for outdoor periods.",
        "tomorrow": "Tomorrow's forecast",
        "disclaimer": DISCLAIMER,
        "advice": {
            "GREEN": "Normal outdoor activities are fine.",
            "YELLOW": "Shorten outdoor play, move strenuous activity to the safest hours, and keep students with breathing problems indoors.",
            "RED": "Move PE and assembly indoors, keep windows closed, and avoid outdoor activity.",
            "UNKNOWN": "There is not enough forecast data to classify this period.",
        },
    },
    "Hindi": {
        "average": "स्कूल समय में औसत PM2.5",
        "peak": "अधिकतम",
        "best": "बाहरी गतिविधि के लिए बेहतर समय",
        "avoid": "बाहर से बचें",
        "unavailable": "उपलब्ध नहीं",
        "sensitive": "संवेदनशील विद्यार्थियों के लिए: बाहरी समय में अंदर की गतिविधियों पर विचार करें।",
        "tomorrow": "कल का पूर्वानुमान",
        "disclaimer": "केवल जानकारी के लिए, चिकित्सा सलाह नहीं।",
        "advice": {
            "GREEN": "सामान्य बाहरी गतिविधियाँ ठीक हैं।",
            "YELLOW": "बाहर खेलने का समय कम करें, कठिन गतिविधियाँ सबसे सुरक्षित समय पर रखें, और सांस की समस्या वाले विद्यार्थियों को अंदर रखें।",
            "RED": "पीटी और सभा अंदर करें, खिड़कियाँ बंद रखें, और बाहरी गतिविधियों से बचें।",
            "UNKNOWN": "इस समय के लिए स्थिति बताने हेतु पर्याप्त पूर्वानुमान डेटा नहीं है।",
        },
    },
    "Marathi": {
        "average": "शाळेच्या वेळेतील सरासरी PM2.5",
        "peak": "कमाल",
        "best": "बाहेरील कृतीसाठी चांगली वेळ",
        "avoid": "बाहेर जाणे टाळा",
        "unavailable": "उपलब्ध नाही",
        "sensitive": "संवेदनशील विद्यार्थ्यांसाठी: बाहेरील वेळेसाठी घरातील कृतींचा विचार करा.",
        "tomorrow": "उद्याचा अंदाज",
        "disclaimer": "फक्त माहितीसाठी, वैद्यकीय सल्ला नाही.",
        "advice": {
            "GREEN": "नेहमीच्या बाहेरील क्रिया ठीक आहेत.",
            "YELLOW": "बाहेर खेळण्याचा वेळ कमी करा, जोरदार क्रिया सुरक्षित वेळेत ठेवा आणि श्वासाचा त्रास असलेल्या विद्यार्थ्यांना घरात ठेवा.",
            "RED": "पीटी आणि सभा घरात घ्या, खिडक्या बंद ठेवा आणि बाहेरील क्रिया टाळा.",
            "UNKNOWN": "या वेळेची स्थिती ठरवण्यासाठी पुरेसा अंदाज उपलब्ध नाही.",
        },
    },
}


def _window_label(window: dict | None, unavailable: str) -> str:
    if not window:
        return unavailable
    start = window.get("start")
    end = window.get("end")
    if isinstance(start, datetime) and isinstance(end, datetime):
        return f"{start:%H:%M}-{end:%H:%M}"
    return unavailable


def template_message(
    school_name: str,
    status: str,
    average_pm25: float | None,
    peak_pm25: float | None,
    best_window: dict | None,
    worst_window: dict | None,
    *,
    language: str = "English",
    advice: str,
    sensitive: bool = False,
    forecast_target: str = "today",
) -> str:
    """Create a message from known values only; no AI-generated facts."""
    labels = _TEXT.get(language, _TEXT["English"])
    average = labels["unavailable"] if average_pm25 is None else f"{average_pm25:.1f}"
    peak = labels["unavailable"] if peak_pm25 is None else f"{peak_pm25:.1f}"
    alert_title = f"Air alert for {school_name}: {status}"
    if forecast_target == "tomorrow":
        alert_title = f"{labels['tomorrow']}: {alert_title}"
    lines = [
        alert_title,
        f"{labels['average']}: {average} µg/m³ ({labels['peak']} {peak}).",
        f"{labels['best']}: {_window_label(best_window, labels['unavailable'])}",
        f"{labels['avoid']}: {_window_label(worst_window, labels['unavailable'])}",
    ]
    if sensitive and status in {"YELLOW", "RED"}:
        lines.append(labels["sensitive"])
    lines.extend((advice, labels["disclaimer"]))
    return "\n".join(lines)


def alert_subject(status: str, school_name: str) -> str:
    """Build the required bounded SNS subject."""
    prefix = f"Air Alert {status}: "
    return f"{prefix}{school_name[: max(0, 100 - len(prefix))]}"


def localized_advice(status: str, language: str = "English") -> str:
    labels = _TEXT.get(language, _TEXT["English"])
    return labels["advice"].get(status, labels["advice"]["UNKNOWN"])


def ai_message(
    school_name: str,
    status: str,
    advice: str,
    summary: dict,
    language: str,
    model_id: str | None = None,
    *,
    bedrock_client=None,
    forecast_target: str = "today",
) -> str:
    """Ask Bedrock for a short message; use a fact-only template on any issue."""
    labels = _TEXT.get(language, _TEXT["English"])
    fallback = template_message(
        school_name,
        status,
        summary.get("average_pm25"),
        summary.get("peak_pm25"),
        summary.get("best_window"),
        summary.get("worst_window"),
        language=language,
        advice=advice,
        sensitive=summary.get("sensitive", False),
        forecast_target=forecast_target,
    )
    if model_id is None:
        from app.deps import get_settings

        model_id = get_settings().bedrock_model
    if not model_id:
        return fallback

    facts = {
        "school_name": school_name,
        "status": status,
        "average_pm25": summary.get("average_pm25"),
        "peak_pm25": summary.get("peak_pm25"),
        "advice": advice,
        "best_window": _window_label(summary.get("best_window"), "Unavailable"),
        "worst_window": _window_label(summary.get("worst_window"), "Unavailable"),
        "language": language,
        "forecast_target": forecast_target,
        "sensitive_notice": labels["sensitive"] if summary.get("sensitive") else "",
        "disclaimer": labels["disclaimer"],
    }
    prompt = (
        "Write a friendly school air-alert message using only the supplied facts. "
        "Use simple language, no more than 60 words, no medical claims, no extra "
        "facts, include the exact status word and supplied disclaimer, and include "
        "the sensitive notice when present. Return only the message. Facts: "
        f"{json.dumps(facts, ensure_ascii=False)}"
    )
    try:
        client = bedrock_client or boto3.client(
            "bedrock-runtime",
            config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1}),
        )
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 180, "temperature": 0.2},
        )
        blocks = response.get("output", {}).get("message", {}).get("content", [])
        generated = " ".join(
            block["text"].strip()
            for block in blocks
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ).strip()
        if (
            not generated
            or len(generated.split()) > 60
            or status.upper() not in generated.upper()
            or labels["disclaimer"] not in generated
            or (
                forecast_target == "tomorrow"
                and labels["tomorrow"] not in generated
            )
            or (
                summary.get("sensitive")
                and labels["sensitive"] not in generated
            )
        ):
            return fallback
        return generated
    except Exception:  # noqa: BLE001 - Bedrock is optional and template text is safe
        return fallback
