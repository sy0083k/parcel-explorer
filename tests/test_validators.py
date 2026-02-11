import pandas as pd

from app.validators import land_validators


def test_validate_required_columns_missing():
    df = pd.DataFrame({"소재지(지번)": ["x"]})
    missing = land_validators.validate_required_columns(df)
    assert "(공부상)지목" in missing
    assert "(공부상)면적(㎡)" in missing


def test_normalize_upload_rows_reports_errors():
    df = pd.DataFrame(
        {
            "소재지(지번)": ["", "addr"],
            "(공부상)지목": ["답", "전"],
            "(공부상)면적(㎡)": ["not-a-number", 12.5],
            "행정재산": ["Y", "N"],
            "일반재산": ["N", "Y"],
            "담당자연락처": ["010", "011"],
        }
    )
    normalized, errors, total_errors = land_validators.normalize_upload_rows(df)
    assert total_errors == 1
    assert len(normalized) == 1
    assert len(errors) == 1
