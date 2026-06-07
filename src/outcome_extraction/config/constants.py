"""Constants for outcome measure extraction."""

# Sentinel value for missing data
NOT_FOUND_VALUE = "Not Found"

# Valid statistical types for MeasureResult.stat_type
STAT_TYPES = [
    "MEAN", "MEDIAN", "HR", "HAZARD_RATIO", "OR", "ODDS_RATIO",
    "RR", "RISK_RATIO", "COUNT", "PERCENT", "RATE",
    "AUC", "CMAX", "TMAX",
    "CHANGE_FROM_BASELINE", "DIFFERENCE",
    "ABSOLUTE_RISK_REDUCTION", "NNT",
]

# Valid dispersion types
DISPERSION_TYPES = [None, "SD", "SE", "CI_95", "CI_90", "CI_99", "IQR", "RANGE"]

# Valid p-value operators
P_OPERATORS = [None, "<", "=", ">", "\u2264", "\u2265", "NS"]

# Valid timepoint units
TIMEPOINT_UNITS = [None, "DAYS", "WEEKS", "MONTHS", "YEARS", "HOURS", "PROCEDURE"]

# Conversion factors: timepoint unit -> days
TIMEPOINT_TO_DAYS = {
    "HOURS": 1 / 24,
    "DAYS": 1.0,
    "WEEKS": 7.0,
    "MONTHS": 30.4375,
    "YEARS": 365.25,
    "PROCEDURE": None,  # Cannot normalize procedural timepoints
}

# AI extraction status values
EXTRACTION_STATUSES = ["AUTO_ACCEPTED", "NEEDS_REVIEW", "FAILED"]

# Processing configuration
DEFAULT_CHUNK_SIZE = 4000
DEFAULT_CHUNK_OVERLAP = 200

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
