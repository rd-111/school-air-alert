"""Small in-memory repositories for local development and tests."""


class MemoryRepositories:
    def __init__(self, schools=None, history=None, subscribers=None):
        self._schools = list(schools or [])
        self._history = dict(history or {})
        self._subscribers = dict(subscribers or {})
        self._notification_runs = set()
        self.schools = MemorySchoolRepository(self)
        self.history = MemoryHistoryRepository(self)
        self.subscribers = MemorySubscriberRepository(self)
        self.notifications = MemoryNotificationRepository(self)

    @classmethod
    def with_demo_school(cls):
        return cls(
            schools=[
                {
                    "school_id": "demo-school",
                    "name": "Demo School",
                    "lat": 19.076,
                    "lon": 72.8777,
                    "language": "English",
                    "topic_arn": "",
                    "topic_arn_sensitive": "",
                }
            ]
        )


class MemorySchoolRepository:
    def __init__(self, parent):
        self.parent = parent

    def list_all(self):
        return [dict(school) for school in self.parent._schools]

    def get(self, school_id):
        school = next(
            (row for row in self.parent._schools if row["school_id"] == school_id),
            None,
        )
        return dict(school) if school else None

    def put(self, school):
        self.parent._schools.append(dict(school))


class MemoryHistoryRepository:
    def __init__(self, parent):
        self.parent = parent

    def put(self, record):
        self.parent._history[(record["school_id"], record["date"])] = dict(record)

    def get(self, school_id, date):
        record = self.parent._history.get((school_id, date))
        return dict(record) if record else None

    def latest(self, school_id):
        rows = [record for (key, _), record in self.parent._history.items() if key == school_id]
        return dict(max(rows, key=lambda row: row["date"])) if rows else None

    def list_recent(self, school_id, start_date, end_date):
        return [
            dict(record)
            for (key, date), record in sorted(self.parent._history.items())
            if key == school_id and start_date <= date <= end_date
        ]


class MemorySubscriberRepository:
    def __init__(self, parent):
        self.parent = parent

    def put(self, subscriber):
        key = (subscriber["school_id"], subscriber["contact"])
        self.parent._subscribers[key] = dict(subscriber)

    def list_by_school(self, school_id):
        return [
            dict(row)
            for (key, _), row in self.parent._subscribers.items()
            if key == school_id
        ]

    def find_by_contact(self, contact):
        return [
            dict(row)
            for row in self.parent._subscribers.values()
            if row["contact"] == contact
        ]

    def delete(self, school_id, contact):
        self.parent._subscribers.pop((school_id, contact), None)


class MemoryNotificationRepository:
    def __init__(self, parent):
        self.parent = parent

    def claim(self, run_id, expires_at):
        del expires_at
        if run_id in self.parent._notification_runs:
            return False
        self.parent._notification_runs.add(run_id)
        return True

    def release(self, run_id):
        self.parent._notification_runs.discard(run_id)
