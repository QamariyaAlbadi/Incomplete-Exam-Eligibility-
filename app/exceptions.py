class AgentError(Exception):
    """Base class for all errors the agent raises deliberately (never a raw traceback to the user)."""


class DatabaseUnavailableError(AgentError):
    pass


class RequestNotFoundError(AgentError):
    pass


class NotIncompleteExamRequestError(AgentError):
    pass


class StudentNotFoundError(AgentError):
    pass


class CourseNotFoundError(AgentError):
    pass


class EnrollmentNotFoundError(AgentError):
    """TODO: raised if the student is not actually enrolled in the Course_ID/Section_ID/
    Term the Incomplete_Exam request references."""


class KnowledgeBaseError(AgentError):
    pass


class GeminiUnavailableError(AgentError):
    """Raised internally when Gemini cannot be reached; callers fall back to a deterministic summary."""
