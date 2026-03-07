class BaseEvent:
    """Base class for all internal events."""
    
    def __init__(self, **kwargs):
        self.payload = kwargs

    def __str__(self):
        return f"<{self.__class__.__name__} {self.payload}>"
