from geaiq_mdp.report import Reportable, format_message_markdown
import pandas as pd
#import pytest


def test_report_info_instance_dataframe():
    report = Reportable()
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    instance = {"c": 5, "d": 6}
    report.info("test", [instance, df])
    format_message_markdown({"report": report.report})


if __name__ == "__main__":
    test_report_info_instance_dataframe()