import arcade
import pyglet


class EventSource:
    """Event source class"""

    __dispatcher: pyglet.event.EventDispatcher = None

    @classmethod
    def set_dispatcher(cls, dispatcher: pyglet.event.EventDispatcher):
        """Set the dispatcher to the specified window."""
        cls.__dispatcher = dispatcher or arcade.get_window()

    def __init__(self, name: str):
        """Create a new event dispatcher."""
        self.__name = name

    def __call__(self, *args, **kwargs):
        """Invoke the dispatcher for this event."""
        window = self.__class__._EventSource__dispatcher
        window.dispatch_event(self.__name, *args, **kwargs)
