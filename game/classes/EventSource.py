import arcade
import pyglet


class EventSource:
    r"""
    A class that can be used to dispatch events to the window from another thread.
    There could be a better way, but I didn't have time to figure it out. (JWS)

    Note that you must register your custom events with pyglet before using this class.

    Example:

    .. code-block:: python

        ChessGame.register_event_type("on_player_move")  # Sent when player moves a piece

    """
    __dispatcher: pyglet.event.EventDispatcher = None

    @classmethod
    def set_dispatcher(cls, dispatcher: pyglet.event.EventDispatcher):
        """Set the dispatcher to the specified Window object."""
        cls.__dispatcher = dispatcher

    @classmethod
    def get_dispatcher(cls) -> pyglet.event.EventDispatcher:
        """Get the dispatcher."""
        return cls.__dispatcher or arcade.get_window()

    def __init__(self, name: str):
        """Create a new event dispatcher."""
        self.__name = name

    def __call__(self, *args):
        """Queue the event on the main message loop."""
        dispatcher = EventSource.get_dispatcher()
        if dispatcher is None:
            raise RuntimeError("No dispatcher set.")
        try:
            pyglet.app.platform_event_loop.post_event(dispatcher, self.__name, *args)
        except Exception as e:
            print(f"Error dispatching event {self.__name}: {e}")
            raise e
