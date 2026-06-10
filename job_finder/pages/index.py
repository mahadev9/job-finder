from typing import Any

import reflex as rx

from job_finder.state import AppState

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


def sort_header(
    label: str,
    col: str,
    sort_col_var,
    sort_asc_var,
    on_sort,
) -> rx.Component:
    return rx.table.column_header_cell(
        rx.hstack(
            rx.text(label, size="2", weight="medium"),
            rx.cond(
                sort_col_var == col,
                rx.cond(
                    sort_asc_var,
                    rx.icon("chevron-up", size=11),
                    rx.icon("chevron-down", size=11),
                ),
                rx.icon("chevrons-up-down", size=11, color="var(--gray-6)"),
            ),
            spacing="1",
            align="center",
            cursor="pointer",
            on_click=on_sort,
        )
    )


def date_input(
    value: Any,
    on_change: Any,
    disabled: Any = False,
    min_val: Any = "",
    max_val: Any = "",
) -> rx.Component:
    return rx.el.input(
        type="date",
        value=value,
        on_change=on_change,
        disabled=disabled,
        min=min_val,
        max=max_val,
        style=_DATE_INPUT_STYLE,
    )


def pagination_bar(
    range_label: Any,
    page: Any,
    page_count: Any,
    on_prev: Any,
    on_next: Any,
) -> rx.Component:
    return rx.hstack(
        rx.text(range_label, size="2", color_scheme="gray"),
        rx.spacer(),
        rx.hstack(
            rx.text("Show", size="2", color_scheme="gray"),
            rx.select.root(
                rx.select.trigger(size="1"),
                rx.select.content(
                    rx.select.item("10", value="10"),
                    rx.select.item("20", value="20"),
                    rx.select.item("50", value="50"),
                    rx.select.item("100", value="100"),
                ),
                value=AppState.page_size_str,
                on_change=AppState.set_page_size,
            ),
            rx.separator(orientation="vertical", size="1"),
            rx.button(
                rx.icon("chevron_left", size=14),
                on_click=on_prev,
                disabled=page == 0,
                variant="ghost",
                color_scheme="gray",
                size="1",
            ),
            rx.text(page + 1, " / ", page_count, size="2", color_scheme="gray"),
            rx.button(
                rx.icon("chevron_right", size=14),
                on_click=on_next,
                disabled=page >= page_count - 1,
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
    )


# Navbar


def navbar() -> rx.Component:
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
                rx.text(
                    "Scan portals · match with AI · track applications",
                    size="2",
                    color_scheme="gray",
                ),
                rx.link(
                    rx.hstack(
                        rx.icon("bar-chart-2", size=14),
                        rx.text("Token Usage", size="2"),
                        spacing="1",
                        align="center",
                    ),
                    href="/usage",
                    color_scheme="gray",
                    underline="none",
                ),
                rx.select.root(
                    rx.select.trigger(size="1", variant="ghost"),
                    rx.select.content(
                        rx.foreach(
                            AppState.available_models,
                            lambda m: rx.select.item(m, value=m),
                        ),
                    ),
                    value=AppState.selected_model,
                    on_change=AppState.set_selected_model,
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


# Pipeline section


def _search_popover_content(
    items_var,
    selected_var,
    search_var,
    on_search,
    on_toggle,
    on_clear,
    placeholder: str,
    on_select_all=None,
) -> rx.Component:
    action_row = rx.hstack(
        rx.button(
            "Clear All",
            on_click=on_clear,
            variant="ghost",
            size="1",
            color_scheme="gray",
            flex="1",
        ),
        *(
            [
                rx.button(
                    "Select All",
                    on_click=on_select_all,
                    variant="ghost",
                    size="1",
                    color_scheme="indigo",
                    flex="1",
                )
            ]
            if on_select_all is not None
            else []
        ),
        width="100%",
        spacing="1",
    )
    return rx.popover.content(
        rx.vstack(
            rx.input(
                placeholder=placeholder,
                value=search_var,
                on_change=on_search,
                size="2",
                width="100%",
            ),
            action_row,
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(
                        items_var,
                        lambda item: rx.checkbox(
                            item,
                            checked=selected_var.contains(item),
                            on_change=on_toggle(item),
                            size="2",
                        ),
                    ),
                    align="start",
                    spacing="2",
                    min_width="180px",
                    padding_right="8px",
                ),
                max_height="400px",
                type="auto",
            ),
            spacing="4",
            align="start",
        ),
        side="bottom",
        align="start",
    )


def fetch_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge("1", variant="solid", color_scheme="indigo", radius="full"),
                rx.text("Fetch New Jobs", weight="bold", size="3"),
                spacing="2",
                align="center",
            ),
            rx.text(
                "Scan all enabled portals and save new listings to the database.",
                size="2",
                color_scheme="gray",
            ),
            rx.hstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Companies", size="1", color_scheme="gray"),
                        rx.popover.root(
                            rx.popover.trigger(
                                rx.button(
                                    AppState.fetch_companies_label,
                                    rx.icon("chevron-down", size=12),
                                    variant="surface",
                                    size="2",
                                    min_width="160px",
                                    justify="between",
                                    disabled=AppState.is_running,
                                )
                            ),
                            _search_popover_content(
                                AppState.filtered_fetch_companies,
                                AppState.fetch_companies,
                                AppState.fetch_companies_search,
                                AppState.set_fetch_companies_search,
                                AppState.toggle_fetch_company,
                                AppState.clear_fetch_companies,
                                "Search companies…",
                                AppState.select_all_fetch_companies,
                            ),
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Queries", size="1", color_scheme="gray"),
                        rx.popover.root(
                            rx.popover.trigger(
                                rx.button(
                                    AppState.fetch_queries_label,
                                    rx.icon("chevron-down", size=12),
                                    variant="surface",
                                    size="2",
                                    min_width="160px",
                                    justify="between",
                                    disabled=AppState.is_running,
                                )
                            ),
                            _search_popover_content(
                                AppState.filtered_fetch_queries,
                                AppState.fetch_queries,
                                AppState.fetch_queries_search,
                                AppState.set_fetch_queries_search,
                                AppState.toggle_fetch_query,
                                AppState.clear_fetch_queries,
                                "Search queries…",
                                AppState.select_all_fetch_queries,
                            ),
                        ),
                        spacing="1",
                        align="start",
                    ),
                    spacing="2",
                    align="end",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("search", size=14),
                    "Fetch New Jobs",
                    on_click=AppState.run_fetch,
                    disabled=AppState.is_running,
                    color_scheme="indigo",
                    size="2",
                    variant="solid",
                ),
                align="end",
                width="100%",
            ),
            width="100%",
            height="100%",
            align="start",
            spacing="3",
        ),
        width="100%",
        flex="1",
    )


def match_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge("2", variant="solid", color_scheme="violet", radius="full"),
                rx.text("Run Match Pipeline", weight="bold", size="3"),
                spacing="2",
                align="center",
            ),
            rx.text(
                "Score unmatched jobs against your profile using AI.",
                size="2",
                color_scheme="gray",
            ),
            rx.hstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("For date", size="1", color_scheme="gray"),
                        date_input(
                            AppState.match_date,
                            AppState.set_match_date,
                            AppState.is_running,
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Batch", size="1", color_scheme="gray"),
                        rx.select.root(
                            rx.select.trigger(size="1"),
                            rx.select.content(
                                rx.select.item("2", value="2"),
                                rx.select.item("5", value="5"),
                                rx.select.item("10", value="10"),
                            ),
                            value=AppState.match_batch_size_str,
                            on_change=AppState.set_match_batch_size,
                            disabled=AppState.is_running,
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Source", size="1", color_scheme="gray"),
                        rx.select.root(
                            rx.select.trigger(size="1"),
                            rx.select.content(
                                rx.select.item("All", value="all"),
                                rx.select.item("Pipeline", value="system"),
                                rx.select.item("Manual", value="user"),
                            ),
                            value=AppState.match_created_by,
                            on_change=AppState.set_match_created_by,
                            disabled=AppState.is_running,
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Companies", size="1", color_scheme="gray"),
                        rx.popover.root(
                            rx.popover.trigger(
                                rx.button(
                                    AppState.match_companies_label,
                                    rx.icon("chevron-down", size=12),
                                    variant="surface",
                                    size="2",
                                    min_width="160px",
                                    justify="between",
                                    disabled=AppState.is_running,
                                )
                            ),
                            _search_popover_content(
                                AppState.filtered_match_companies,
                                AppState.match_companies,
                                AppState.match_companies_search,
                                AppState.set_match_companies_search,
                                AppState.toggle_match_company,
                                AppState.clear_match_companies,
                                "Search companies…",
                                AppState.select_all_match_companies,
                            ),
                        ),
                        spacing="1",
                        align="start",
                    ),
                    spacing="2",
                    align="end",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("cpu", size=14),
                    "Run Match",
                    on_click=AppState.run_match,
                    disabled=AppState.is_running,
                    color_scheme="violet",
                    size="2",
                ),
                align="end",
                width="100%",
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        width="100%",
        flex="1",
    )


def pipeline_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            fetch_card(),
            match_card(),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        rx.cond(
            AppState.is_running,
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text(AppState.status_text, size="2", weight="medium"),
                        rx.spacer(),
                        rx.button(
                            rx.icon("square", size=12),
                            "Stop",
                            on_click=AppState.stop_pipeline,
                            size="1",
                            variant="soft",
                            color_scheme="red",
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                    ),
                    rx.progress(
                        value=AppState.progress_pct,
                        width="100%",
                        color_scheme=rx.cond(
                            AppState.running == "fetch", "indigo", "violet"
                        ),
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="100%",
                variant="surface",
            ),
        ),
        result_banner(),
        width="100%",
        spacing="3",
    )


# Result banner


def result_banner() -> rx.Component:
    return rx.cond(
        AppState.has_result,
        rx.box(
            rx.hstack(
                rx.text(
                    AppState.result_message,
                    size="2",
                    weight="medium",
                    color=rx.cond(
                        AppState.result_kind == "success",
                        "var(--green-11)",
                        rx.cond(
                            AppState.result_kind == "warning",
                            "var(--amber-11)",
                            "var(--red-11)",
                        ),
                    ),
                ),
                rx.spacer(),
                rx.button(
                    "Dismiss",
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                    on_click=AppState.dismiss_result,
                    cursor="pointer",
                ),
                align="center",
                width="100%",
            ),
            padding="12px",
            border_radius="var(--radius-3)",
            background=rx.cond(
                AppState.result_kind == "success",
                "var(--green-2)",
                rx.cond(
                    AppState.result_kind == "warning",
                    "var(--amber-2)",
                    "var(--red-2)",
                ),
            ),
            border=rx.cond(
                AppState.result_kind == "success",
                "1px solid var(--green-6)",
                rx.cond(
                    AppState.result_kind == "warning",
                    "1px solid var(--amber-6)",
                    "1px solid var(--red-6)",
                ),
            ),
            width="100%",
        ),
    )


# Live jobs feed


def live_job_row(job: Any) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(job.company, size="2", weight="medium")),
        rx.table.cell(rx.text(job.role, size="2")),
        rx.table.cell(
            rx.badge(job.portal, variant="soft", color_scheme="indigo", size="1")
        ),
        rx.table.cell(
            rx.link(
                rx.hstack(rx.icon("external_link", size=12), "Open", spacing="1"),
                href=job.link,
                is_external=True,
                size="2",
                color_scheme="gray",
            )
        ),
    )


def live_jobs_panel() -> rx.Component:
    return rx.cond(
        AppState.running == "fetch",
        rx.cond(
            AppState.has_new_jobs,
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("zap", size=15, color="var(--amber-9)"),
                        rx.text("Live — Newly Found Jobs", weight="bold", size="3"),
                        rx.spacer(),
                        rx.badge(
                            AppState.new_job_count,
                            " new",
                            variant="soft",
                            color_scheme="amber",
                            size="2",
                        ),
                        align="center",
                        spacing="2",
                        width="100%",
                    ),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Company"),
                                rx.table.column_header_cell("Role"),
                                rx.table.column_header_cell("Portal"),
                                rx.table.column_header_cell(""),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(AppState.new_jobs, live_job_row),
                        ),
                        size="1",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
                width="100%",
            ),
        ),
    )


# Fetched jobs tab


def fetched_job_row(job: Any) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(job.company, weight="bold", size="2"),
            min_width="160px",
        ),
        rx.table.cell(rx.text(job.role, size="2")),
        rx.table.cell(
            rx.badge(job.portal, variant="soft", color_scheme="indigo", size="1")
        ),
        rx.table.cell(
            rx.cond(
                job.created_by == "user",
                rx.badge("Manual", variant="soft", color_scheme="violet", size="1"),
                rx.badge("Pipeline", variant="soft", color_scheme="gray", size="1"),
            ),
            min_width="80px",
        ),
        rx.table.cell(
            rx.text(job.fetched_date, size="1", color_scheme="gray"),
            min_width="100px",
        ),
        rx.table.cell(
            rx.cond(
                job.pipeline_ran,
                rx.badge(
                    rx.icon("check", size=10),
                    "Ran",
                    variant="soft",
                    color_scheme="green",
                    size="1",
                ),
                rx.badge(
                    "Pending",
                    variant="soft",
                    color_scheme="gray",
                    size="1",
                ),
            ),
            min_width="80px",
        ),
        rx.table.cell(
            rx.link(
                rx.hstack(rx.icon("external_link", size=12), "Open", spacing="1"),
                href=job.link,
                is_external=True,
                size="2",
                color_scheme="gray",
            )
        ),
        align="center",
    )


def manual_job_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Add Job Manually"),
            rx.vstack(
                rx.vstack(
                    rx.text("Company *", size="2", weight="medium"),
                    rx.input(
                        placeholder="e.g. Anthropic",
                        value=AppState.manual_job_company,
                        on_change=AppState.set_manual_job_company,
                        size="2",
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Role *", size="2", weight="medium"),
                    rx.input(
                        placeholder="e.g. AI Engineer",
                        value=AppState.manual_job_role,
                        on_change=AppState.set_manual_job_role,
                        size="2",
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Link *", size="2", weight="medium"),
                    rx.input(
                        placeholder="https://jobs.example.com/...",
                        value=AppState.manual_job_link,
                        on_change=AppState.set_manual_job_link,
                        size="2",
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Portal", size="2", weight="medium"),
                    rx.input(
                        placeholder="Auto-detected from URL (e.g. greenhouse, ashby, linkedin)",
                        value=AppState.manual_job_portal,
                        on_change=AppState.set_manual_job_portal,
                        size="2",
                        width="100%",
                    ),
                    rx.text(
                        "Leave blank to auto-detect from the link.",
                        size="1",
                        color_scheme="gray",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.cond(
                    AppState.manual_job_error != "",
                    rx.text(
                        AppState.manual_job_error,
                        size="2",
                        color="var(--red-11)",
                    ),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                            size="2",
                        ),
                    ),
                    rx.button(
                        rx.icon("plus", size=14),
                        "Add Job",
                        on_click=AppState.submit_manual_job,
                        color_scheme="indigo",
                        size="2",
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                    padding_top="8px",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="480px",
        ),
        open=AppState.manual_job_open,
        on_open_change=AppState.set_manual_job_open,
    )


def fetched_jobs_section() -> rx.Component:
    return rx.vstack(
        manual_job_dialog(),
        rx.hstack(
            rx.heading("Fetched Jobs", size="5", weight="bold"),
            rx.badge(
                AppState.fetched_job_count_label,
                variant="soft",
                color_scheme="gray",
                size="2",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("plus", size=14),
                    on_click=AppState.open_manual_job_dialog,
                    variant="soft",
                    color_scheme="indigo",
                    size="2",
                    title="Add job manually",
                ),
                rx.popover.root(
                    rx.popover.trigger(
                        rx.button(
                            AppState.fetched_company_filter_label,
                            rx.icon("chevron-down", size=12),
                            variant="surface",
                            size="2",
                            min_width="160px",
                            justify="between",
                        )
                    ),
                    _search_popover_content(
                        AppState.filtered_distinct_fetched_companies,
                        AppState.fetched_company_filter,
                        AppState.fetched_company_filter_search,
                        AppState.set_fetched_company_filter_search,
                        AppState.toggle_fetched_company_filter,
                        AppState.clear_fetched_company_filter,
                        "Search companies…",
                        AppState.select_all_fetched_company_filter,
                    ),
                ),
                rx.select.root(
                    rx.select.trigger(placeholder="All", size="2"),
                    rx.select.content(
                        rx.select.item("All", value="all"),
                        rx.select.item("Ran", value="ran"),
                        rx.select.item("Pending", value="pending"),
                    ),
                    value=AppState.fetched_pipeline_ran_filter,
                    on_change=AppState.set_fetched_pipeline_ran_filter,
                ),
                rx.vstack(
                    rx.text("From", size="1", color_scheme="gray"),
                    date_input(
                        AppState.fetched_from_date,
                        AppState.set_fetched_from_date,
                        max_val=AppState.fetched_to_date,
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("To", size="1", color_scheme="gray"),
                    date_input(
                        AppState.fetched_to_date,
                        AppState.set_fetched_to_date,
                        min_val=AppState.fetched_from_date,
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
        rx.cond(
            ~AppState.has_fetched_jobs,
            rx.center(
                rx.vstack(
                    rx.icon("inbox", size=40, color="var(--gray-7)"),
                    rx.text(
                        "No fetched jobs yet.",
                        size="3",
                        color_scheme="gray",
                        weight="medium",
                    ),
                    rx.text(
                        "Click 'Fetch New Jobs' to scan enabled portals.",
                        size="2",
                        color_scheme="gray",
                    ),
                    align="center",
                    spacing="2",
                ),
                padding_y="64px",
                width="100%",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        sort_header(
                            "Company",
                            "company",
                            AppState.fetched_sort_col,
                            AppState.fetched_sort_asc,
                            AppState.sort_fetched("company"),
                        ),
                        rx.table.column_header_cell("Role"),
                        rx.table.column_header_cell("Portal"),
                        rx.table.column_header_cell("Source"),
                        sort_header(
                            "Fetched",
                            "fetched_ts",
                            AppState.fetched_sort_col,
                            AppState.fetched_sort_asc,
                            AppState.sort_fetched("fetched_ts"),
                        ),
                        rx.table.column_header_cell("Pipeline"),
                        rx.table.column_header_cell(""),
                    ),
                ),
                rx.table.body(
                    rx.foreach(AppState.fetched_page_items, fetched_job_row),
                ),
                size="2",
                width="100%",
                variant="surface",
            ),
        ),
        pagination_bar(
            AppState.fetched_range_label,
            AppState.fetched_page,
            AppState.fetched_page_count,
            AppState.fetched_prev_page,
            AppState.fetched_next_page,
        ),
        spacing="4",
        width="100%",
        align="start",
    )


# Matched jobs tab


def job_row(job: Any) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(job.company, weight="bold", size="2"),
            min_width="160px",
        ),
        rx.table.cell(
            rx.vstack(
                rx.link(
                    job.role,
                    href=job.role_link,
                    is_external=True,
                    size="2",
                    underline="hover",
                ),
                rx.cond(
                    job.reason != "",
                    rx.text(
                        "↳ ",
                        job.reason,
                        size="1",
                        color_scheme="gray",
                    ),
                ),
                spacing="1",
                align="start",
            ),
        ),
        rx.table.cell(
            rx.badge(
                job.score_label,
                color_scheme=job.score_color,
                variant="soft",
                size="2",
            ),
            min_width="80px",
        ),
        rx.table.cell(
            rx.select.root(
                rx.select.trigger(
                    variant="soft",
                    size="1",
                    color_scheme=job.status_color,
                ),
                rx.select.content(
                    rx.select.item("Pending", value="pending"),
                    rx.select.item("Interested", value="interested"),
                    rx.select.item("Applied", value="applied"),
                    rx.select.item("Rejected", value="rejected"),
                    rx.select.item("Not Interested", value="not_interested"),
                    rx.select.item("Low Match", value="low_match"),
                ),
                value=job.status,
                on_change=AppState.update_job_status(job.id),
            ),
            min_width="130px",
        ),
        rx.table.cell(
            rx.cond(
                job.status_changed_at != "",
                rx.text(job.status_changed_at, size="1", color_scheme="gray"),
                rx.text("—", size="1", color_scheme="gray"),
            ),
            min_width="100px",
        ),
        align="center",
    )


def jobs_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Matched Jobs", size="5", weight="bold"),
            rx.badge(
                AppState.job_count_label,
                variant="soft",
                color_scheme="gray",
                size="2",
            ),
            rx.spacer(),
            rx.hstack(
                rx.popover.root(
                    rx.popover.trigger(
                        rx.button(
                            AppState.company_filter_label,
                            rx.icon("chevron-down", size=12),
                            variant="surface",
                            size="2",
                            min_width="160px",
                            justify="between",
                        )
                    ),
                    _search_popover_content(
                        AppState.filtered_distinct_companies,
                        AppState.company_filter,
                        AppState.company_filter_search,
                        AppState.set_company_filter_search,
                        AppState.toggle_company_filter,
                        AppState.clear_company_filter,
                        "Search companies…",
                        AppState.select_all_company_filter,
                    ),
                ),
                rx.select.root(
                    rx.select.trigger(placeholder="All Statuses", size="2"),
                    rx.select.content(
                        rx.select.item("All Statuses", value="all"),
                        rx.select.item("Pending", value="pending"),
                        rx.select.item("Interested", value="interested"),
                        rx.select.item("Applied", value="applied"),
                        rx.select.item("Rejected", value="rejected"),
                        rx.select.item("Not Interested", value="not_interested"),
                        rx.select.item("Low Match", value="low_match"),
                    ),
                    value=AppState.status_filter,
                    on_change=AppState.set_status_filter,
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Score", size="1", color_scheme="gray"),
                        rx.spacer(),
                        rx.badge(
                            AppState.score_range[0],
                            " – ",
                            AppState.score_range[1],
                            variant="soft",
                            color_scheme="violet",
                            size="1",
                        ),
                        width="176px",
                        align="center",
                    ),
                    rx.hstack(
                        rx.text("0", size="1", color="var(--gray-9)"),
                        rx.slider(
                            default_value=AppState.score_range,
                            min=0,
                            max=10,
                            step=1,
                            on_value_commit=AppState.set_score_range,
                            color_scheme="violet",
                            size="1",
                            flex="1",
                        ),
                        rx.text("10", size="1", color="var(--gray-9)"),
                        spacing="2",
                        align="center",
                        width="176px",
                    ),
                    gap="10px",
                    align="start",
                    padding_bottom="6px",
                ),
                rx.vstack(
                    rx.text("From", size="1", color_scheme="gray"),
                    date_input(
                        AppState.from_date,
                        AppState.set_from_date,
                        max_val=AppState.to_date,
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("To", size="1", color_scheme="gray"),
                    date_input(
                        AppState.to_date,
                        AppState.set_to_date,
                        min_val=AppState.from_date,
                    ),
                    spacing="1",
                ),
                spacing="3",
                align="end",
                wrap="wrap",
            ),
            align="center",
            width="100%",
            wrap="wrap",
            gap="3",
        ),
        rx.cond(
            ~AppState.has_jobs,
            rx.center(
                rx.vstack(
                    rx.icon("inbox", size=40, color="var(--gray-7)"),
                    rx.text(
                        "No matched jobs yet.",
                        size="3",
                        color_scheme="gray",
                        weight="medium",
                    ),
                    rx.text(
                        "Fetch new jobs first, then run the match pipeline.",
                        size="2",
                        color_scheme="gray",
                    ),
                    align="center",
                    spacing="2",
                ),
                padding_y="64px",
                width="100%",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        sort_header(
                            "Company",
                            "company",
                            AppState.jobs_sort_col,
                            AppState.jobs_sort_asc,
                            AppState.sort_jobs("company"),
                        ),
                        rx.table.column_header_cell("Role"),
                        sort_header(
                            "Score",
                            "score",
                            AppState.jobs_sort_col,
                            AppState.jobs_sort_asc,
                            AppState.sort_jobs("score"),
                        ),
                        sort_header(
                            "Status",
                            "status",
                            AppState.jobs_sort_col,
                            AppState.jobs_sort_asc,
                            AppState.sort_jobs("status"),
                        ),
                        rx.table.column_header_cell("Changed"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(AppState.jobs_page_items, job_row),
                ),
                size="2",
                width="100%",
                variant="surface",
            ),
        ),
        pagination_bar(
            AppState.jobs_range_label,
            AppState.jobs_page,
            AppState.jobs_page_count,
            AppState.jobs_prev_page,
            AppState.jobs_next_page,
        ),
        spacing="4",
        width="100%",
        align="start",
    )


# Page


def index() -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            rx.vstack(
                pipeline_section(),
                live_jobs_panel(),
                rx.separator(width="100%"),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Fetched Jobs", value="fetched"),
                        rx.tabs.trigger("Matched Jobs", value="matched"),
                    ),
                    rx.tabs.content(
                        fetched_jobs_section(),
                        value="fetched",
                        padding_top="16px",
                    ),
                    rx.tabs.content(
                        jobs_section(),
                        value="matched",
                        padding_top="16px",
                    ),
                    default_value="fetched",
                    width="100%",
                ),
                spacing="6",
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
