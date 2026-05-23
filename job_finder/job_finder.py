import reflex as rx

from .pages.index import index
from .state import AppState

app = rx.App()
app.add_page(index, route="/", on_load=AppState.on_load)
