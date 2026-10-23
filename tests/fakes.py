"""Minimal SQL boundary replacement; filesystem operations remain real.

This is deliberately not a PostgreSQL/RLS implementation or integration test.
"""
import copy
import re
from contextlib import contextmanager
from uuid import UUID, uuid4

from psycopg.errors import CheckViolation, ForeignKeyViolation, OperationalError


class Result:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class Store:
    def __init__(self, users=()):
        self.users = set(users)
        self.documents = {}
        self.versions = {}
        self.folders = {}
        self.fail_version_insert = False
        self.fail_commit = False
        self.allow_cross_user_folder = False
        self.before_version_insert = None

    @contextmanager
    def transaction(self, settings, user_id):
        previous = copy.deepcopy((self.documents, self.versions, self.folders))
        try:
            yield Connection(self, UUID(str(user_id)))
        except BaseException:
            self.documents, self.versions, self.folders = previous
            raise
        else:
            if self.fail_commit:
                self.documents, self.versions, self.folders = previous
                raise OperationalError("simulated uncertain COMMIT result")


class Connection:
    def __init__(self, store, user_id):
        self.store = store
        self.user_id = user_id

    def execute(self, query, params=()):
        sql = " ".join(query.lower().split())
        store = self.store
        if sql.startswith("select id from rag.users"):
            return Result((self.user_id,) if self.user_id in store.users else None)
        if sql.startswith("select id") and "from rag.documents" in sql:
            document = store.documents.get(params[0])
            if not document or document["user_id"] != self.user_id or document.get("deleted_at"):
                return Result()
            if "latest_version_id" in sql:
                return Result((document["id"], document.get("latest_version_id")))
            return Result((document["id"],))
        if sql.startswith("select") and "from rag.document_versions" in sql:
            versions = [v for v in store.versions.values()
                        if v["document_id"] == params[0] and v["user_id"] == self.user_id]
            latest = max(versions, key=lambda v: v["version_no"], default=None)
            if "max(version_no)" in sql:
                return Result(((latest["version_no"] + 1) if latest else None,))
            if not latest:
                return Result()
            if sql.startswith("select raw_sha256"):
                return Result((latest["raw_sha256"],))
            return Result(tuple(latest[k] for k in ("id", "version_no", "raw_sha256", "storage_key")))
        if sql.startswith("insert into"):
            match = re.search(r"insert into rag\.(\w+)\s*\(([^)]+)\)", sql)
            table, columns = match.groups()
            row = dict(zip((column.strip() for column in columns.split(",")), params))
            row.setdefault("id", uuid4())
            if row.get("user_id") != self.user_id:
                raise AssertionError("attempted to insert another user's row")
            if table == "folders":
                store.folders[row["id"]] = row
            elif table == "documents":
                folder = store.folders.get(row.get("folder_id"))
                if folder and folder["user_id"] != self.user_id and not store.allow_cross_user_folder:
                    raise ForeignKeyViolation("simulated composite folder FK")
                row.setdefault("latest_version_id", None)
                store.documents[row["id"]] = row
            elif table == "document_versions":
                if store.before_version_insert:
                    store.before_version_insert()
                if store.fail_version_insert:
                    raise CheckViolation("simulated version insert failure")
                store.versions[row["id"]] = row
            else:
                raise AssertionError(sql)
            return Result((row["id"],))
        if sql.startswith("update rag.documents set latest_version_id"):
            store.documents[params[1]]["latest_version_id"] = params[0]
            return Result()
        if sql.startswith("delete from rag.documents"):
            row = store.documents.get(params[0])
            if row and row["user_id"] == self.user_id:
                del store.documents[params[0]]
            return Result()
        if sql.startswith("delete from rag.folders"):
            row = store.folders.get(params[0])
            if row and row["user_id"] == self.user_id:
                del store.folders[params[0]]
            return Result()
        raise AssertionError("Unexpected SQL in boundary replacement: " + sql)
