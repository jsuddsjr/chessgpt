import pyglet

class ApiEventTargetMixin(pyglet.event.EventDispatcher):
    @classmethod
    def start_listening(cls):
        """Start listening for events"""
        cls._event_listeners = {}

    def dispatch_event(self, event: str, *args, **kwargs):
        """Dispatch an event"""
        if event not in self._event_listeners:
            return
        for callback in self._event_listeners[event]:
            callback(*args, **kwargs)

    def on(self, event: str, callback: callable):
        """Add an event listener"""
        pyglet.event.EventDispatcher.register_event_type(event)
        self.push_handlers(callback)