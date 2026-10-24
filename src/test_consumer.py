import json
from kafka import KafkaConsumer

c = KafkaConsumer("transactions", bootstrap_servers="localhost:9092",
                  auto_offset_reset="earliest", consumer_timeout_ms=15000,
                  value_deserializer=lambda v: json.loads(v.decode("utf-8")))
n = 0
for m in c:
    n += 1
    if n <= 5: print(m.value)
print("received", n, "messages")
