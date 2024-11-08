from shiny import reactive
from shiny.express import input, render, ui
import ibis
import pandas as pd
from plotnine import (
    ggplot,
    aes,
    geom_boxplot,
    labs,
    scale_fill_manual,
    theme,
    theme_minimal,
)
import faicons as fa

con = ibis.snowflake.connect(
    warehouse="DEFAULT_WH",
    database="HEART_FAILURE",
    schema="PUBLIC",
    connection_name="workbench",
)

# Connect to the table and filter the data
heart_failure = con.table("HEART_FAILURE")
heart_failure_df = heart_failure.execute()

comparison = (
    heart_failure_df.groupby(["DEATH_EVENT", "DIABETES"])
    .agg(
        median_age=("AGE", "median"),
        median_serum_creatinine=("SERUM_CREATININE", "median"),
        median_serum_sodium=("SERUM_SODIUM", "median"),
    )
    .replace(
        {"DEATH_EVENT": {1: "Died", 0: "Survived"}, "DIABETES": {1: "Yes", 0: "No"}}
    )
    .rename(
        columns={
            "DEATH_EVENT": "Outcome",
            "DIABETES": "Diabetes",
            "median_age": "Median Age",
            "median_serum_creatinine": "Median Serum Creatinine",
            "median_serum_sodium": "Median Serum Sodium",
        }
    )
)

metric_choices = {
    "AGE": "Age",
    "SERUM_SODIUM": "Serum Sodium",
    "SERUM_CREATININE": "Serum Creatinine",
}

ui.page_opts(
    title="Heart Failure Data Dashboard",
    fillable=True,
    theme=ui.Theme(preset="sandstone"),
)

with ui.sidebar():
    ui.input_selectize(
        id="metric", label="Select a clinical metric:", choices=metric_choices
    )

with ui.layout_columns():
    with ui.card():
        ui.card_header("Clinical Metric Distribution by Survival")

        heart_failure_df["DEATH_EVENT_STR"] = heart_failure_df["DEATH_EVENT"].astype(
            str
        )
        heart_failure_df["DIABETES"] = heart_failure_df["DIABETES"].astype(str)
        heart_failure_df["AGE"] = heart_failure_df["AGE"].astype(float)

        @render.plot
        def metric_plot():
            return (
                ggplot(
                    heart_failure_df,
                    aes(x="DEATH_EVENT_STR", y=input.metric(), fill="DIABETES"),
                )
                + geom_boxplot()
                + scale_fill_manual(values=["#29abe0", "#f57b3b"])
                + labs(
                    title="Serum Sodium Levels by Diabetes Status and Survival Outcome",
                    x="Survival Outcome (0 = Survived, 1 = Died)",
                    y=metric_choices[input.metric()],
                    fill="Diabetes",
                )
                + theme_minimal()
                + theme(legend_position="bottom")
            )

    with ui.layout_column_wrap(width=1):
        with ui.card():
            ui.card_header("Summary Statistics")

            @render.data_frame
            def summary_table():
                return comparison

        with ui.card():
            ui.card_header("Key Values")

            with ui.layout_columns():
                ui.value_box(
                    title="Total Patients",
                    value=len(heart_failure_df),
                    showcase=fa.icon_svg("user", style="regular"),
                    theme="primary",
                )
                ui.value_box(
                    title="Median Age",
                    value=round(heart_failure_df["AGE"].median()),
                    showcase=fa.icon_svg("calendar", style="regular"),
                    theme="info",
                )
                ui.value_box(
                    title="Survival Rate",
                    value=f"{round((1 - heart_failure_df['DEATH_EVENT'].mean()) * 100)}%",
                    showcase=fa.icon_svg("heart", style="regular"),
                    theme="warning",
                )
