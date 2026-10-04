class DomainError(Exception):
    """Plain domain failure, independent of Django and HTTP implementation."""

    def __init__(self, message, code="validation_error", status=400, fields=None, location=None, current_version=None):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status
        self.fields, self.location, self.current_version = fields or {}, location, current_version

    def payload(self):
        return {"error": {"code": self.code, "message": self.message, "fields": self.fields,
                          "location": self.location, "current_version": self.current_version}}
