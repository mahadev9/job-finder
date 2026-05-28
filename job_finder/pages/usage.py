from typing import Any

import reflex as rx

from job_finder.state import UsageState

_DATE_INPUT_STYLE: dict = {
    "padding": "0px 8px",
    "height": "32px",
    "border": "1px solid var(--gray-a7)",
    "border_radius": "var(--radius-2)",
    "font_size": "13px",
    "font_family": "inherit",
    "color": "var(--gray-12)",
    "background": "var(--color-surface)",
    "cursor": "pointer",
}


def _stat_card(label: str, value: Any, color: str = "gray") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(label, size="2", color_scheme="gray", weight="medium"),
            rx.text(value, size="6", weight="bold", color_scheme=color),
            spacing="1",
            align="start",
        ),
        flex="1",
        min_width="140px",
    )


def _usage_navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("briefcase", size=20, color="var(--violet-9)"),
                rx.heading("Job Finder", size="5", weight="bold"),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.link(
                    rx.hstack(
                        rx.icon("arrow-left", size=14),
                        rx.text("Jobs", size="2"),
                        spacing="1",
                        align="center",
                    ),
                    href="/",
                    color_scheme="gray",
                    underline="none",
                ),
                rx.color_mode.button(variant="ghost", size="2"),
                spacing="3",
                align="center",
            ),
            width="100%",
            align="center",
            padding_x="24px",
            padding_y="12px",
        ),
        background="var(--color-panel-solid)",
        border_bottom="1px solid var(--gray-a4)",
        position="sticky",
        top="0",
        z_index="10",
        width="100%",
    )


def _usage_row(row: Any) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row.created_at, size="2", color_scheme="gray")),
        rx.table.cell(
            rx.badge(
                row.pipeline,
                variant="soft",
                color_scheme=rx.match(
                    row.pipeline,
                    ("fetch", "indigo"),
                    ("match", "violet"),
                    "gray",
                ),
                size="1",
            )
        ),
        rx.table.cell(rx.text(row.model, size="2")),
        rx.table.cell(rx.text(row.input_tokens, size="2"), align="right"),
        rx.table.cell(rx.text(row.output_tokens, size="2"), align="right"),
        rx.table.cell(rx.text(row.reasoning_tokens, size="2"), align="right"),
        rx.table.cell(rx.text(row.total_tokens, size="2", weight="medium"), align="right"),
        rx.table.cell(
            rx.text(row.request_id, size="1", color_scheme="gray", font_family="monospace")
        ),
        align="center",
    )


def usage() -> rx.Component:
    return rx.box(
        _usage_navbar(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("bar-chart-2", size=20, color="var(--violet-9)"),
                    rx.heading("Token Usage", size="5", weight="bold"),
                    spacing="2",
                    align="center",
                    padding_bottom="4px",
                ),
                # Stat cards
                rx.hstack(
                    _stat_card("Total Calls", UsageState.usage_total_count, "gray"),
                    _stat_card("Input Tokens", UsageState.usage_total_input_fmt, "blue"),
                    _stat_card("Output Tokens", UsageState.usage_total_output_fmt, "violet"),
                    _stat_card("Reasoning Tokens", UsageState.usage_total_reasoning_fmt, "amber"),
                    _stat_card("Total Tokens", UsageState.usage_total_tokens_fmt, "indigo"),
                    spacing="4",
                    width="100%",
                    wrap="wrap",
                ),
                rx.separator(width="100%"),
                # Filters + table heading
                rx.hstack(
                    rx.hstack(
                        rx.icon("bar-chart-2", size=16, color="var(--gray-9)"),
                        rx.text("Usage Log", weight="bold", size="3"),
                        rx.badge(
                            UsageState.usage_total_count,
                            " records",
                            variant="soft",
                            color_scheme="gray",
                            size="2",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.select.root(
                            rx.select.trigger(
                                placeholder="All Pipelines", size="2"
                            ),
                            rx.select.content(
                                rx.select.item("All Pipelines", value="all"),
                                rx.select.item("Fetch", value="fetch"),
                                rx.select.item("Match", value="match"),
                            ),
                            value=UsageState.usage_pipeline_filter,
                            on_change=UsageState.set_usage_pipeline_filter,
                        ),
                        rx.vstack(
                            rx.text("From", size="1", color_scheme="gray"),
                            rx.el.input(
                                type="date",
                                value=UsageState.usage_from_date,
                                on_change=UsageState.set_usage_from_date,
                                max=UsageState.usage_to_date,
                                style=_DATE_INPUT_STYLE,
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("To", size="1", color_scheme="gray"),
                            rx.el.input(
                                type="date",
                                value=UsageState.usage_to_date,
                                on_change=UsageState.set_usage_to_date,
                                min=UsageState.usage_from_date,
                                style=_DATE_INPUT_STYLE,
                            ),
                            spacing="1",
                        ),
                        spacing="3",
                        align="end",
                    ),
                    align="center",
                    width="100%",
                    wrap="wrap",
                    gap="3",
                ),
                # Table
                rx.cond(
                    UsageState.usage_total_count == 0,
                    rx.center(
                        rx.vstack(
                            rx.icon("activity", size=40, color="var(--gray-7)"),
                            rx.text(
                                "No usage recorded yet.",
                                size="3",
                                color_scheme="gray",
                                weight="medium",
                            ),
                            rx.text(
                                "Run a fetch or match pipeline to start tracking.",
                                size="2",
                                color_scheme="gray",
                            ),
                            align="center",
                            spacing="2",
                        ),
                        padding_y="64px",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Date (EST)"),
                                    rx.table.column_header_cell("Pipeline"),
                                    rx.table.column_header_cell("Model"),
                                    rx.table.column_header_cell(
                                        rx.text("Input", text_align="right")
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Output", text_align="right")
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Reasoning", text_align="right")
                                    ),
                                    rx.table.column_header_cell(
                                        rx.text("Total", text_align="right")
                                    ),
                                    rx.table.column_header_cell("Request ID"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(UsageState.usage_rows, _usage_row)
                            ),
                            size="2",
                            width="100%",
                            variant="surface",
                        ),
                        rx.hstack(
                            rx.text(
                                UsageState.usage_range_label,
                                size="2",
                                color_scheme="gray",
                            ),
                            rx.spacer(),
                            rx.hstack(
                                rx.button(
                                    rx.icon("chevron_left", size=14),
                                    on_click=UsageState.usage_prev_page,
                                    disabled=UsageState.usage_page == 0,
                                    variant="ghost",
                                    color_scheme="gray",
                                    size="1",
                                ),
                                rx.text(
                                    UsageState.usage_page + 1,
                                    " / ",
                                    UsageState.usage_page_count,
                                    size="2",
                                    color_scheme="gray",
                                ),
                                rx.button(
                                    rx.icon("chevron_right", size=14),
                                    on_click=UsageState.usage_next_page,
                                    disabled=UsageState.usage_page
                                    >= UsageState.usage_page_count - 1,
                                    variant="ghost",
                                    color_scheme="gray",
                                    size="1",
                                ),
                                align="center",
                                spacing="2",
                            ),
                            align="center",
                            width="100%",
                            padding_top="8px",
                        ),
                        width="100%",
                        spacing="2",
                    ),
                ),
                spacing="5",
                width="100%",
                align="start",
            ),
            padding_x="24px",
            padding_y="20px",
            width="100%",
        ),
        min_height="100vh",
        background="var(--gray-1)",
        width="100%",
    )
