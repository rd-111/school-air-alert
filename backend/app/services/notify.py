"""SNS alert publishing with a bounded, secret-safe failure log."""

import json
import logging

import boto3
from botocore.config import Config

from app.services.messages import alert_subject

logger = logging.getLogger(__name__)


def _sns_client():
    return boto3.client(
        "sns",
        config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1}),
    )


def create_school_topics(school_id: str, *, sns_client=None) -> tuple[str, str]:
    """Create deterministic regular and sensitive topics for one school."""
    client = sns_client or _sns_client()
    regular = client.create_topic(Name=f"school-air-alert-{school_id}-regular")["TopicArn"]
    sensitive = client.create_topic(
        Name=f"school-air-alert-{school_id}-sensitive"
    )["TopicArn"]
    return regular, sensitive


def subscribe_email(topic_arn: str, email: str, *, sns_client=None) -> str:
    """Request an SNS email subscription; confirmation is performed by AWS."""
    client = sns_client or _sns_client()
    response = client.subscribe(
        TopicArn=topic_arn,
        Protocol="email",
        Endpoint=email,
        ReturnSubscriptionArn=True,
    )
    return str(response.get("SubscriptionArn", "pending confirmation"))


def publish_alert(
    topic_arn: str,
    school_id: str,
    school_name: str,
    status: str,
    message: str,
    *,
    sns_client=None,
) -> bool:
    """Publish one notification; provider errors do not escape the school run."""
    if not topic_arn:
        return False
    try:
        client = sns_client or _sns_client()
        client.publish(
            TopicArn=topic_arn,
            Subject=alert_subject(status, school_name),
            Message=message,
        )
        return True
    except Exception as exc:  # noqa: BLE001 - SNS failures must not stop other schools
        logger.warning(
            json.dumps(
                {
                    "event": "sns_publish_failed",
                    "school_id": school_id,
                    "reason": type(exc).__name__,
                }
            )
        )
        return False
