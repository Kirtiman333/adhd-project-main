class EventManager:
    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_type, callback):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event_type, data=None):
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                if data is not None:
                    callback(data)
                else:
                    callback()
    """

    Observer pattern đơn giản để quản lý sự kiện giữa các 
    module mà không cần chúng phải biết về nhau.
    Ví dụ: UIManager có thể phát sự kiện "state_change" 
    khi người dùng đăng nhập thành công, và GameManager 
    sẽ lắng nghe sự kiện này để chuyển sang menu mà 
    không cần UIManager phải gọi trực tiếp GameManager.

    không xóa, ko là quên mất hết :)))
    """