from collections import defaultdict
from itertools import chain, combinations
from pathlib import Path

import numpy as np
import pandas as pd


def check_quality(filepath: Path) -> dict:

    """Inspect a DataFrame and return a data-quality report."""

    # ========================================================
    # CONFIGURATION
    # ========================================================

    chunk_size = 30_000
    MAX_UNIQUE_VALUE = 1_000 # Threshold for low-cardinality columns 
    sentinel_values = (
        # Whitespace and empty
        "", " ",
        # Symbols & punctuation
        "?", "??", "-", "--", "---", ".", "/", "//", "*", "***",
        # Text / String tokens
        "NA", "N/A", "n/a", "Not Available", "Not Applicable", "null", "Null", "NULL", "(null)", "None", "NONE", "nil", "undefined", "missing", "MISSING", "unknown", "UNKNOWN", "unk", "default", "blank",
        # Floating-point keywords
        "NaN", "nan", "inf", "-inf",
        # Survey refusal & skip codes
        "DK",   # Don't Know
        "REF",  # Refused
        "PNA",  # Prefer Not to Answer
        # Excel / Spreadsheet formula errors
        "#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NUM!", "#NAME?", "#NULL!",
        # Date placeholders
        "1970-01-01", # Unix epoch start
        "1969-12-31", # Day before Unix epoch
        "1900-01-01", # Common default date in spreadsheets
        "1904-01-01", # Mac Excel epoch start
        "0000-00-00", # Invalid date placeholder
        "0001-01-01", # Unitialized date placeholder like .NET and C#
        "9999-12-31", # Far-future placeholder date
    )

    # ==============================================================================
    # 1. STRUCTURAL & SCHEMA TRACKING
    # ==============================================================================
    total_rows = 0                        # int: Cumulative row count across all chunks
    total_cols = 0                        # int: Total column count (extracted from Chunk 0)
    column_names = []                     # list[str]: Ordered list of all column headers

    # baseline_dtypes: Initial column datatypes from Chunk 0 -> {'col': dtype}
    # Used as the ground-truth schema to benchmark subsequent chunks against.
    baseline_dtypes = dict()

    # type_drifts: Flags if a chunk parses a column as a different dtype -> {'col': bool}
    # E.g., pandas reads chunk 0 as int64, but chunk 3 as object due to mixed data or strings.
    type_drifts = defaultdict(bool)

    # ==============================================================================
    # 2. MISSING DATA & SENTINEL PLACEHOLDERS
    # ==============================================================================
    # null_counts: Running sum of standard NA / NaN / None values -> {'col': int}
    # Accumulated using chunk[col].isna().sum().
    null_counts = defaultdict(int)

    # sentinel_counts: Running count of hidden missing tokens -> {'col': int}
    # Catches unparsed strings like '?', 'N/A', 'missing', or 'blank' using .isin(sentinel_values).
    sentinel_counts = defaultdict(int)

    # ==============================================================================
    # 3. NUMERIC HEALTH & SINGLE-VARIABLE (UNIVARIATE) STATS
    # ==============================================================================
    # global_min / global_max: Extreme observed values -> {'col': scalar_val}
    # Tracks lowest and highest real numbers while safely ignoring NaN chunks.
    global_min = dict()
    global_max = dict()

    # numeric_counts: Total non-null numeric observations (n) -> {'col': int}
    # Acts as the valid denominator for running means and variance formulas.
    numeric_counts = defaultdict(int)

    # running_sum: Total accumulated sum (sum(x)) -> {'col': float}
    # Used with numeric_counts to compute the global mean without keeping raw data in RAM.
    running_sum = defaultdict(float)

    # running_sum_sq: Total accumulated sum of squared values (sum(x^2)) -> {'col': float}
    # Powers the one-pass shortcut formula: Var = (sum(x^2) / n) - mean^2.
    running_sum_sq = defaultdict(float)

    # zero_counts: Count of literal 0 / 0.0 entries -> {'col': int}
    # Flags column sparsity and catches zero-division risks for downstream feature engineering.
    zero_counts = defaultdict(int)

    # negative_counts: Count of values < 0 -> {'col': int}
    # Catches business logic violations (e.g., negative age, price) and unmasked numeric sentinels (-1, -99).
    negative_counts = defaultdict(int)

    # ==============================================================================
    # 4. DUPLICATES & UNIQUENESS
    # ==============================================================================
    # Track duplicate rows across chunks
    is_seen = set()  # Global set of row hashes to track duplicates across chunks

    # ==============================================================================
    # 5. PAIRWISE BIVARIATE TRACKING (COVARIANCE)
    # ==============================================================================
    # All pairwise dictionaries use tuple keys: (col_x, col_y) generated via itertools.combinations.
    # These strictly measure rows where BOTH columns have non-null numbers simultaneously.

    # pairwise_counts: Joint non-null row count (n_xy) -> {(col_x, col_y): int}
    pairwise_counts = defaultdict(int)

    # pairwise_sum_x: Running sum of col_x ONLY on overlapping valid rows -> {(col_x, col_y): float}
    pairwise_sum_x = defaultdict(float)

    # pairwise_sum_y: Running sum of col_y ONLY on overlapping valid rows -> {(col_x, col_y): float}
    pairwise_sum_y = defaultdict(float)

    # running_sum_xy: Running sum of cross-products (sum(x * y)) -> {(col_x, col_y): float}
    # Powers the covariance shortcut formula: Cov = (n*sum(xy) - sum(x)*sum(y)) / (n * (n - 1)).
    running_sum_xy = defaultdict(float)


    # ==============================================================================
    # 6. CATEGORICAL & CARDINALITY SETS
    # ==============================================================================
    # unique_values: Set of distinct non-null tokens -> {'col': {val1, val2, ...}}
    # Bounded by MAX_UNIQUE_VALUE to prevent memory explosions on high-cardinality IDs.
    unique_values = defaultdict(set)

    # ----- Spreadsheet loading -----
    
    extension = filepath.suffix.lower()

    if extension == ".csv":
        chunks = pd.read_csv(filepath, chunksize=chunk_size, low_memory=False)

    elif extension in [".xls", ".xlsx"]:
        # Load the Excel file, then yield it in chunks artificially 
        # so it is perfectly compatible with the iteration loop below.
        df = pd.read_excel(filepath, engine="calamine")
        chunks = (df.iloc[i:i + chunk_size] for i in range(0, len(df), chunk_size))

    else:
        raise ValueError(f"Unsupported file extension: {extension}. Only .csv, .xls, and .xlsx are supported.")

    # ----- Data that can be done at once -----

    first_chunk = next(chunks) 

    # Columns
    total_cols = len(first_chunk.columns)
    column_names = first_chunk.columns.tolist()

    # Data Types
    baseline_dtypes = first_chunk.dtypes.to_dict()

    # ----- Accumulate Data Across Chunks -----
    for chunk in chain([first_chunk], chunks):

        # Row count accumulation
        total_rows += len(chunk)

        # Hash each row into a compact 64-bit unsigned integer.
        # Makes it much faster to check for duplicates across chunks instead of comparing entire rows
        # This lets us efficiently detect duplicates across chunks
        # without storing/comparing entire rows.
        row_hashes = pd.util.hash_pandas_object(chunk, index=False)
        is_seen.update(row_hashes)

        # Iterate through each column in the chunk to accumulate metrics
        for col in chunk.columns:

            # Accumulate type drift
            if chunk[col].dtype != baseline_dtypes[col]:
                type_drifts[col] = True  # Mark as drifted

            # Null counts accumulation
            null_counts[col] += chunk[col].isna().sum()

            # Sentinel value counts accumulation
            sentinel_counts[col] += chunk[col].isin(sentinel_values).sum()

            # Unique values accumulation for low-cardinality columns
            if unique_values[col] != "High Cardinality":
                if len(unique_values[col]) <= MAX_UNIQUE_VALUE:
                    unique_values[col].update(chunk[col].dropna().unique())
                
                if len(unique_values[col]) > MAX_UNIQUE_VALUE:
                    unique_values[col].clear()  # Clear to save memory if it exceeds the threshold
                    unique_values[col] = "High Cardinality"        

        # Iterate through numeric columns for min, max, sum, zero, and negative counts
        for col in chunk.select_dtypes(include=['number']).columns:


            chunk_min = chunk[col].min()
            chunk_max = chunk[col].max()

            # Ensure the chunk has non-null values to avoid NA comparisons
            # Accumulate global min
            if pd.notna(chunk_min):  
                if col not in global_min:
                        global_min[col] = chunk_min
                else:
                        global_min[col] = min(global_min[col], chunk_min)

            # Accumulate global max
            if pd.notna(chunk_max): 
                if col not in global_max:
                        global_max[col] = chunk_max
                else:
                        global_max[col] = max(global_max[col], chunk_max)

            # Running sum for mean calculation
            running_sum[col] += chunk[col].sum()
            numeric_counts[col] += chunk[col].count()  # Count of non-null values

            # Zero counts
            zero_counts[col] += (chunk[col] == 0).sum()

            # Negative counts (useful for features that should be strictly positive)
            negative_counts[col] += (chunk[col] < 0).sum()

            # sum of squares for variance calculation
            running_sum_sq[col] += (chunk[col] ** 2).sum()

        numeric_cols = chunk.select_dtypes(include=['number']).columns

        # combinations(list, 2) generates every unique pair of columns
        for col_x, col_y in combinations(numeric_cols, 2):

            # Create a True/False mask for rows where BOTH columns have numbers
            valid_mask = chunk[col_x].notna() & chunk[col_y].notna()

            # Extract only the valid overlapping rows
            valid_x = chunk.loc[valid_mask, col_x]
            valid_y = chunk.loc[valid_mask, col_y]

            # Accumulate the pairwise stats
            pair_key = (col_x, col_y)
            pairwise_counts[pair_key] += valid_mask.sum()
            pairwise_sum_x[pair_key] += valid_x.sum()
            pairwise_sum_y[pair_key] += valid_y.sum()
            running_sum_xy[pair_key] += (valid_x * valid_y).sum()

        del chunk  # Free memory after processing each chunk

    # ----- Finalize Metrics -----

    duplicate_counts = total_rows - len(is_seen)  # Total duplicates across all chunks

    unique_values = {
        col: vals 
        for col, vals in unique_values.items() 
        if isinstance(vals, set) or vals == "High Cardinality"  # isintance check ensures we only keep sets, not the "High Cardinality" string
    } 

    null_percentage = {
        col: (count / total_rows) * 100 
        for col, count in null_counts.items()
    }

    non_null_counts = {
        col: total_rows - count 
        for col, count in null_counts.items()
    }

    non_null_percentage = {
        col: (count / total_rows) * 100 
        for col, count in non_null_counts.items()
    }

    empty_columns = [
        col for col, null_count in null_counts.items()
        if null_count == total_rows
    ]

    global_mean = {
        col: (running_sum[col] / numeric_counts[col])
        if numeric_counts[col] > 0 else None 
        for col in running_sum.keys()
    }

    # Population Variance (Divides by N)
    population_variance = {
        col: (running_sum_sq[col] / numeric_counts[col]) - (global_mean[col] ** 2)
        if numeric_counts[col] > 0 else None 
        for col in running_sum.keys()
    }

    population_std = {
        col: np.sqrt(max(0, population_variance[col])) # max(0, val) prevents float math crashes
        if population_variance[col] is not None else None 
        for col in population_variance
    }

    # Sample Variance (Divides by N - 1)
    sample_variance = {
        col: ((numeric_counts[col] * running_sum_sq[col]) - (running_sum[col] ** 2)) / (numeric_counts[col] * (numeric_counts[col] - 1))
        if numeric_counts[col] > 1 else None 
        for col in running_sum.keys()
    }

    sample_std = {
        col: np.sqrt(max(0, sample_variance[col])) 
        if sample_variance[col] is not None else None 
        for col in sample_variance
    }

    sample_covariance = dict()
    population_covariance = dict()

    # Calculate covariance for every pair we tracked
    for (col_x, col_y), n in pairwise_counts.items():
        if n > 1:
                sum_x = pairwise_sum_x[(col_x, col_y)]
                sum_y = pairwise_sum_y[(col_x, col_y)]
                sum_xy = running_sum_xy[(col_x, col_y)]
                
                # Sample Covariance shortcut formula
                sample_covariance[(col_x, col_y)] = ((n * sum_xy) - (sum_x * sum_y)) / (n * (n - 1))
                
                # Population Covariance shortcut formula
                population_covariance[(col_x, col_y)] = ((n * sum_xy) - (sum_x * sum_y)) / (n ** 2)
        else:
                sample_covariance[(col_x, col_y)] = None
                population_covariance[(col_x, col_y)] = None

    pearson_correlation = dict()

    for (col_x, col_y), cov in sample_covariance.items():
        std_x = sample_std.get(col_x)
        std_y = sample_std.get(col_y)
        
        if cov is not None and std_x and std_y and (std_x * std_y) > 0:
            pearson_correlation[(col_x, col_y)] = cov / (std_x * std_y)
        else:
            pearson_correlation[(col_x, col_y)] = None

    # ==============================================================================
    # FINAL AUDIT REPORT
    # ==============================================================================
    report = {
        # --- Dataset Geometry ---
        "rows": total_rows,                                 # Total row count processed across all chunks
        "columns": total_cols,                              # Total column count
        "column_names": column_names,                       # Ordered column name headers
        "empty_columns": empty_columns,                     # Columns with 100% missing values (null_count == total_rows)

        # --- Schema & Type Integrity ---
        "baseline_dtypes": baseline_dtypes,                 # Initial schema mapping detected in Chunk 0: {'col': dtype}
        "type_drifts": type_drifts,                         # Drift flags: True if a chunk switched types (e.g., int -> object)

        # --- Missingness & Placeholder Audit ---
        "null_counts": null_counts,                         # Raw count of standard nulls (NaN, None) per column
        "null_percentage": null_percentage,                 # Null share of total rows: (null_counts / total_rows) * 100
        "non_null_counts": non_null_counts,                 # Valid row count: (total_rows - null_counts)
        "non_null_percentage": non_null_percentage,         # Completeness rate: (non_null_counts / total_rows) * 100
        "sentinel_counts": sentinel_counts,                 # Count of hidden string markers ('?', 'N/A', 'None') found

        # --- Numeric Health & Bounds ---
        "global_min": global_min,                           # Absolute minimum numeric value per column
        "global_max": global_max,                           # Absolute maximum numeric value per column
        "zero_counts": zero_counts,                         # Count of zeros; indicates sparsity or default zero-fills
        "negative_counts": negative_counts,                 # Count of negative values; flags domain rule breaks (e.g., negative prices)

        # ---- Duplicates & Uniqueness ---
        "duplicate_counts": duplicate_counts,               # Total duplicate rows detected across all chunks

        # --- Central Tendency & Raw Accumulators ---
        "running_sum": running_sum,                         # Global sum of values (sum(x)) per numeric column
        "numeric_counts": numeric_counts,                   # Count of valid numbers evaluated (denominator for mean)
        "global_mean": global_mean,                         # Arithmetic average per column: running_sum / numeric_counts

        # --- Dispersion & Spread (Variability) ---
        "population_variance": population_variance,         # Variance assuming entire population (divided by N)
        "population_std": population_std,                   # Spread in original feature units: sqrt(population_variance)
        "sample_variance": sample_variance,                 # Unbiased sample variance using Bessel's correction (divided by N - 1)
        "sample_std": sample_std,                           # Sample standard deviation: sqrt(sample_variance)

        # --- Bivariate Relationships (Inter-column Direction) ---
        "sample_covariance": sample_covariance,             # Sample covariance between numeric pairs: {(col_a, col_b): cov_val}
        "population_covariance": population_covariance,     # Population covariance between numeric pairs: {(col_a, col_b): cov_val}

        # --- Categorical Cardinality ---
        "unique_values": unique_values,                     # Low-cardinality category values; bounded by MAX_UNIQUE_VALUE
    }

    return report