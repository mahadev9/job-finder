import reflex as rx

config = rx.Config(
    app_name="job_finder",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin,
        rx.plugins.RadixThemesPlugin(
            rx.theme(
                appearance="light",
                accent_color="indigo",
                gray_color="slate",
                radius="medium",
            )
        ),
    ],
)
