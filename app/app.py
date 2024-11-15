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

comparison = (
    heart_failure
    .group_by(["DEATH_EVENT", "DIABETES"])
    .aggregate(
        median_age=heart_failure["AGE"].median(),
        median_serum_creatinine=heart_failure["SERUM_CREATININE"].median(),
        median_serum_sodium=heart_failure["SERUM_SODIUM"].median()
    )
    .mutate(
        DEATH_EVENT=ibis.ifelse(heart_failure["DEATH_EVENT"] == 1, "Died", "Survived"),
        DIABETES=ibis.ifelse(heart_failure["DIABETES"] == 1, "Yes", "No"),
        median_serum_creatinine=heart_failure["SERUM_CREATININE"].median().cast("float64")
    )
    .rename(
        {
            "Survival": "DEATH_EVENT",
            "Diabetes Status": "DIABETES",
            "Median Age": "median_age",
            "Median Creatinine (mg/dL)": "median_serum_creatinine",
            "Median Sodium (mEq/L)": "median_serum_sodium"
        }
    )
    .order_by(ibis.desc("Survival"))
)

metric_choices = {
    "AGE": "Age",
    "SERUM_SODIUM": "Serum Sodium",
    "SERUM_CREATININE": "Serum Creatinine",
}

ui.page_opts(
    title=ui.tags.div(
        ui.tags.img(src="heart.png", height="30px", style="margin-right: 10px;"),
        "Heart Failure Data Dashboard"
    ),
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

        heart_failure_plot = (
            heart_failure
            .mutate(
                DEATH_EVENT=heart_failure["DEATH_EVENT"].cast("string"),
                DIABETES=heart_failure["DIABETES"].cast("string"),
                AGE=heart_failure["AGE"].cast("float")
            )
        )

        @render.plot
        def metric_plot():
            return (
                ggplot(
                    heart_failure_plot,
                    aes(x="DEATH_EVENT", y=input.metric(), fill="DIABETES"),
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
                return comparison.execute()

        with ui.card():
            ui.card_header("Key Values")
            n_patients = int(heart_failure.count().execute())
            median_age = round(float(heart_failure["AGE"].median().execute()))
            survival_rate_str = (
                f"{round((1 - heart_failure['DEATH_EVENT'].mean().execute()) * 100)}%"
            )
            with ui.layout_columns():
                ui.value_box(
                    title="Total Patients",
                    value=n_patients,
                    showcase=fa.icon_svg("user", style="regular"),
                    theme="primary",
                )
                ui.value_box(
                    title="Median Age",
                    value=median_age,
                    showcase=fa.icon_svg("calendar", style="regular"),
                    theme="info",
                )
                ui.value_box(
                    title="Survival Rate",
                    value=survival_rate_str,
                    showcase=fa.icon_svg("heart", style="regular"),
                    theme="warning",
                )
