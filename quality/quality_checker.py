import pandas as pd

def check_quality(df: pd.DataFrame) -> dict:
    """
    Inspect a DataFrame and return a data-quality report.
    """

    # ----- BASIC INFORMATION -----

    rows, columns = df.shape

    basic_info = {
        "rows": rows,
        "columns": columns,
        "size": df.size,
    }

    # ----- COLUMN INFORMATION -----

    column_info = {}

    for column in df.columns:
        series = df[column]

        column_info[column] = {
            "dtype": str(series.dtype),
            "non_null": int(series.notna().sum()),
            "missing": int(series.isna().sum()),
            "missing_percentage": (
                float(series.isna().mean() * 100)
            ),
            "unique": int(series.nunique(dropna=True)),
            "is_empty": bool(series.isna().all()),
            "is_constant": bool(series.nunique(dropna=False) <= 1)
        }

    # ----- MISSING VALUES -----

    missing = df.isna().sum()

    missing_info = {
        column: {
            "count": int(count),
            "percentage": float((count / rows) * 100) if rows > 0 else 0.0,
        }
        for column, count in missing.items()
        if count > 0
    }

    total_missing = int(missing.sum())

    # ----- DUPLICATES -----

    duplicate_count = int(df.duplicated().sum())

    duplicate_percentage = (
        float((duplicate_count / rows) * 100)
        if rows > 0
        else 0.0
    )

    duplicates = {
        "count": duplicate_count,
        "percentage": duplicate_percentage,
    }

    # ----- UNIQUE VALUES -----

    unique_values = {
        column: int(df[column].nunique())
        for column in df.columns
    }
 
    # ----- NUMERICAL STATISTICS -----

    numerical_columns = df.select_dtypes(include="number").columns.tolist()

    if numerical_columns:
        statistics = df[numerical_columns].describe().to_dict()
    else:
        statistics = {}

    # ----- DATA TYPES -----

    data_types = {
        column: str(dtype)
        for column, dtype in df.dtypes.items()
    }

    # -----EMPTY COLUMNS -----

    empty_columns = [
        column
        for column in df.columns
        if df[column].isna().all()
    ]

    # ----- CONSTANT COLUMNS -----

    constant_columns = [
        column
        for column in df.columns
        if df[column].nunique(dropna=False) <= 1
    ]

    # ----- FINAL REPORT -----

    report = {
        "basic_info": basic_info,
        "columns": column_info,
        "missing_values": {
            "total": total_missing,
            "by_column": missing_info,
        },
        "duplicates": duplicates,
        "unique_values": unique_values,
        "statistics": statistics,
        "data_types": data_types,
        "empty_columns": empty_columns,
        "constant_columns": constant_columns,
    }

    return report
