import reflex as rx

from .pages.index import index
from .pages.usage import usage
from .state import AppState, UsageState

app = rx.App()
app.add_page(index, route="/", on_load=AppState.on_load)
app.add_page(usage, route="/usage", on_load=UsageState.on_load)
