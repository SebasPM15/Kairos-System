class DomainError(Exception):
    """Base class for errors that handlers translate into user-facing messages."""


class ProjectNotFound(DomainError):
    pass


class ActiveLimitReached(DomainError):
    pass


class NextActionRequired(DomainError):
    pass


class MilestoneNotFound(DomainError):
    pass


class IdeaNotFound(DomainError):
    pass


class DecisionNotFound(DomainError):
    pass
