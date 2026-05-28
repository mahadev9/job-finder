import reflex as rx

config = rx.Config(
    app_name="job_finder",
    show_built_with_reflex=False,
    stylesheets=["custom.css"],
    plugins=[
        rx.plugins.SitemapPlugin,
        rx.plugins.RadixThemesPlugin(
            rx.theme(
                appearance="dark",
                accent_color="violet",
                gray_color="slate",
                radius="medium",
                has_background=True,
            )
        ),
    ],
)
