from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource, ValueType
from feast.types import Float64, Int64

card = Entity(name="card_id", join_keys=["card_id"], value_type=ValueType.INT64)

source = FileSource(
    path="../data/features.parquet",
    timestamp_field="event_timestamp",
)

card_features = FeatureView(
    name="card_features",
    entities=[card],
    ttl=timedelta(days=365),
    schema=[
        Field(name="hour", dtype=Int64),
        Field(name="day_of_week", dtype=Int64),
        Field(name="tx_count_before", dtype=Int64),
        Field(name="secs_since_last", dtype=Float64),
        Field(name="amt_vs_avg", dtype=Float64),
        Field(name="device_changed", dtype=Int64),
        Field(name="addr_changed", dtype=Int64),
        Field(name="email_changed", dtype=Int64),
    ],
    source=source,
)
