import uuid


class DomainError(Exception):
    """Base class for domain-specific errors."""


class SchemaNotFoundError(DomainError):
    def __init__(self, schema_id: uuid.UUID) -> None:
        self.schema_id = schema_id
        super().__init__(f"Schema {schema_id} not found.")


class VersionNotFoundError(DomainError):
    def __init__(self, schema_id: uuid.UUID, version_number: int) -> None:
        self.schema_id = schema_id
        self.version_number = version_number
        super().__init__(f"Version {version_number} of schema {schema_id} not found.")


class VersionConflictError(DomainError):
    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Schema was modified in the meantime (expected version {expected}, "
            f"latest is {actual}). Reload it and try again."
        )


class SchemaGenerationError(DomainError):
    """The agent failed to generate a valid schema specification."""


class EmailAlreadyRegisteredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Email already registered.")


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Incorrect email or password.")
