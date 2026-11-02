# W7 network suite: summary

## demo: 21 tests x 1 run(s): 21 PASS / 0 FAIL

| Test | Result | Repro | Key measurements (run1) |
|---|---|---|---|
| `test_NET01_no_hang_during_outage` | PASS | 1/1 | status_answered_of_5=5 |
| `test_NET02_backoff_grows_no_reconnect_storm` | PASS | 1/1 | attempts_20s=6; backoff_seq_first10=[500, 1000, 2000, 4000, 8000, 8000] |
| `test_NET03_recovery_after_net_up` | PASS | 1/1 | recovery_ms=0.3; state_after=CONNECTED |
| `test_BUF01_offline_messages_are_buffered` | PASS | 1/1 | queued_ids=[1, 2, 3, 4, 5]; buffer_line=["[BUFFER] count=5 capacity=8 dropped=0"] |
| `test_BUF02_buffer_flushed_exactly_once` | PASS | 1/1 | queued=[1, 2, 3, 4, 5]; published=[1, 2, 3, 4, 5]; status={"net": "CONNECTED", "broker": true, "buffer": 0, "capacity": 8, "sent": 5, "dropped": 0, "duplicates": 0, "reconnect_attempts": 2, "heap": 286847} |
| `test_BUF03_capacity_boundary_counters[7]` | PASS | 1/1 | sent_offline=7; buffer=7; dropped=0 |
| `test_BUF03_capacity_boundary_counters[8]` | PASS | 1/1 | sent_offline=8; buffer=8; dropped=0 |
| `test_BUF03_capacity_boundary_counters[9]` | PASS | 1/1 | sent_offline=9; buffer=8; dropped=1 |
| `test_BUF03_capacity_boundary_counters[12]` | PASS | 1/1 | sent_offline=12; buffer=8; dropped=4 |
| `test_BUF04_drop_oldest_keeps_newest_in_order[8]` | PASS | 1/1 | queued=[1, 2, 3, 4, 5, 6, 7, 8]; published=[1, 2, 3, 4, 5, 6, 7, 8]; lost_ids=[] |
| `test_BUF04_drop_oldest_keeps_newest_in_order[9]` | PASS | 1/1 | queued=[1, 2, 3, 4, 5, 6, 7, 8, 9]; published=[2, 3, 4, 5, 6, 7, 8, 9]; lost_ids=[1] |
| `test_BUF04_drop_oldest_keeps_newest_in_order[12]` | PASS | 1/1 | queued=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]; published=[5, 6, 7, 8, 9, 10, 11, 12]; lost_ids=[1, 2, 3, 4] |
| `test_DUP01_no_duplicate_ids_over_5_flaps` | PASS | 1/1 | published_total=15; unique_ids=15; status_duplicates=0 |
| `test_MEM01_heap_trend_online_stress` | PASS | 1/1 | heap_series=[286847, 286847, 286847, 286847, 286847, 286847, 286847, 286847, 286847, 286847, 286847]; delta_bytes=0; bytes_per_message=0.0 |
| `test_MEM02_heap_and_buffer_offline_stress` | PASS | 1/1 | heap_series=[286847, 286847, 286847, 286847, 286847, 286847]; buffer_occupancy_offline=[8, 8, 8, 8, 8] |
| `test_OBS01_status_has_required_fields` | PASS | 1/1 | fields=["broker", "buffer", "capacity", "dropped", "duplicates", "heap", "net", "reconnect_attempts", "sent"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[HELP]` | PASS | 1/1 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[stress 5]` | PASS | 1/1 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[NET]` | PASS | 1/1 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[NET SIDEWAYS]` | PASS | 1/1 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[STATUSX]` | PASS | 1/1 | response=["[CLI] ERROR unknown command"] |

## buggy: 21 tests x 3 run(s): 11 PASS / 10 FAIL

| Test | Result | Repro | Key measurements (run1) |
|---|---|---|---|
| `test_NET01_no_hang_during_outage` | PASS | 3/3 | status_answered_of_5=5 |
| `test_NET02_backoff_grows_no_reconnect_storm` | FAIL | 3/3 | attempts_20s=369; backoff_seq_first10=[500, 50, 50, 50, 50, 50, 50, 50, 50, 50] |
| `test_NET03_recovery_after_net_up` | PASS | 3/3 | recovery_ms=0.5; state_after=CONNECTED |
| `test_BUF01_offline_messages_are_buffered` | PASS | 3/3 | queued_ids=[1, 2, 3, 4, 5]; buffer_line=["[NET] state=CONNECTING", "[NET] reconnect=FAILED", "[NET] state=BACKOFF", "[NET] retry=8 backoff_ms=50", "[BUFFER] count=5 capacity=8 dropped=0", "[NET] state=CONNECTING", "[NET] |
| `test_BUF02_buffer_flushed_exactly_once` | FAIL | 3/3 | queued=[1, 2, 3, 4, 5]; published=[1, 1, 2, 2, 3, 3, 4, 4, 5, 5]; status={"net": "CONNECTED", "broker": true, "buffer": 0, "capacity": 8, "sent": 10, "dropped": 0, "duplicates": 5, "reconnect_attempts": 8, "heap": 286527 |
| `test_BUF03_capacity_boundary_counters[7]` | PASS | 3/3 | sent_offline=7; buffer=7; dropped=0 |
| `test_BUF03_capacity_boundary_counters[8]` | PASS | 3/3 | sent_offline=8; buffer=8; dropped=0 |
| `test_BUF03_capacity_boundary_counters[9]` | FAIL | 3/3 | sent_offline=9; buffer=9; dropped=0 |
| `test_BUF03_capacity_boundary_counters[12]` | FAIL | 3/3 | sent_offline=12; buffer=12; dropped=0 |
| `test_BUF04_drop_oldest_keeps_newest_in_order[8]` | FAIL | 3/3 | queued=[1, 2, 3, 4, 5, 6, 7, 8]; published=[1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8]; lost_ids=[] |
| `test_BUF04_drop_oldest_keeps_newest_in_order[9]` | FAIL | 3/3 | queued=[1, 2, 3, 4, 5, 6, 7, 8, 9]; published=[9, 9, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9]; lost_ids=[1] |
| `test_BUF04_drop_oldest_keeps_newest_in_order[12]` | FAIL | 3/3 | queued=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]; published=[9, 9, 10, 10, 11, 11, 12, 12, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12]; lost_ids=[1, 2, 3, 4] |
| `test_DUP01_no_duplicate_ids_over_5_flaps` | FAIL | 3/3 | published_total=30; unique_ids=15; status_duplicates=15 |
| `test_MEM01_heap_trend_online_stress` | FAIL | 3/3 | heap_series=[286847, 280447, 274047, 267647, 261247, 254847, 248447, 242047, 235647, 229247, 222847]; delta_bytes=-64000; bytes_per_message=64.0 |
| `test_MEM02_heap_and_buffer_offline_stress` | FAIL | 3/3 | heap_series=[286847, 280447, 274047, 267647, 261247, 254847]; buffer_occupancy_offline=[100, 100, 100, 100, 100] |
| `test_OBS01_status_has_required_fields` | PASS | 3/3 | fields=["broker", "buffer", "capacity", "dropped", "duplicates", "heap", "net", "reconnect_attempts", "sent"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[HELP]` | PASS | 3/3 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[stress 5]` | PASS | 3/3 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[NET]` | PASS | 3/3 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[NET SIDEWAYS]` | PASS | 3/3 | response=["[CLI] ERROR unknown command"] |
| `test_NEG01_unknown_command_rejected_without_side_effects[STATUSX]` | PASS | 3/3 | response=["[CLI] ERROR unknown command"] |

