# Test summary

## buggy: 124 tests x 3 run(s) -> 78 passed, 46 failed

- test_SW01_wakeup_time_within_15pct[10]  fail 3/3 — AssertionError: deep sleep lasted 1000 ms, expected 8500..11500 ms for `sleep 10`
assert 8500.0 <= 1000.14408
- test_SW01_wakeup_time_within_15pct[1]  fail 3/3 — AssertionError: deep sleep lasted 100 ms, expected 850..1150 ms for `sleep 1`
assert 850.0 <= 100.15672
- test_SW01_wakeup_time_within_15pct[2]  fail 3/3 — AssertionError: deep sleep lasted 200 ms, expected 1700..2300 ms for `sleep 2`
assert 1700.0 <= 200.36386999999996
- test_SW01_wakeup_time_within_15pct[30]  fail 3/3 — AssertionError: deep sleep lasted 3000 ms, expected 25500..34500 ms for `sleep 30`
assert 25500.0 <= 3000.17911
- test_SW01_wakeup_time_within_15pct[5]  fail 3/3 — AssertionError: deep sleep lasted 500 ms, expected 4250..5750 ms for `sleep 5`
assert 4250.0 <= 500.14036000000004
- test_SW01_wakeup_time_within_15pct[60]  fail 3/3 — AssertionError: deep sleep lasted 6000 ms, expected 51000..69000 ms for `sleep 60`
assert 51000.0 <= 6000.1458
- test_SW04_repeated_sleep_wake_cycles  fail 3/3 — AssertionError: 10/10 wake-ups outside 1700..2300 ms: [200, 201, 200, 200, 200, 200, 201, 200, 201, 200]
assert not [200, 201, 200, 200, 200, 200, ...]
- test_WDT03_relay_off_after_wdt_reset[button]  fail 3/3 — AssertionError: relay pin is ON after WDT reset (unsafe actuator state)
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e1259f40>.relay
- test_WDT03_relay_off_after_wdt_reset[cli]  fail 3/3 — AssertionError: relay pin is ON after WDT reset (unsafe actuator state)
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e134f3e0>.relay
- test_WDT03_relay_off_after_wdt_reset[cli_then_save]  fail 3/3 — AssertionError: relay pin is ON after WDT reset (unsafe actuator state)
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e125a210>.relay
- test_WDT05_repeated_hang_recovery_x10  fail 3/3 — AssertionError: relay ON after WDT reset in 10/10 cycles
assert [1, 1, 1, 1, 1, 1, ...] == [0, 0, 0, 0, 0, 0, ...]
  
  At index 0 diff: 1 != 0
  Use -v to get more diff
- test_BO02_relay_off_after_brownout[button]  fail 3/3 — AssertionError: relay is ON after brown-out reset
assert (1 == 0)
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e0164050>.relay
- test_BO02_relay_off_after_brownout[cli]  fail 3/3 — AssertionError: relay is ON after brown-out reset
assert (1 == 0)
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e125bb60>.relay
- test_BO03_brownout_during_boot[150]  fail 3/3 — AssertionError: relay ON after brown-out recovery
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e0165a90>.relay
- test_BO03_brownout_during_boot[300]  fail 3/3 — AssertionError: relay ON after brown-out recovery
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e0166120>.relay
- test_BO03_brownout_during_boot[320]  fail 3/3 — AssertionError: relay ON after brown-out recovery
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e01667b0>.relay
- test_BO03_brownout_during_boot[400]  fail 3/3 — AssertionError: relay ON after brown-out recovery
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e1258c80>.relay
- test_BO03_brownout_during_boot[50]  fail 3/3 — AssertionError: relay ON after brown-out recovery
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e0165400>.relay
- test_BO03_brownout_during_boot[5]  fail 3/3 — AssertionError: relay ON after brown-out recovery
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7e0164b90>.relay
- test_BO04_random_brownouts_x10[1]  fail 3/3 — AssertionError: relay ON after brown-out in 2/10 recoveries
assert [0, 0, 0, 0, 0, 0, ...] == [0, 0, 0, 0, 0, 0, ...]
  
  At index 8 diff: 1 != 0
  Use -v to get more diff
- test_BO04_random_brownouts_x10[2]  fail 3/3 — AssertionError: relay ON after brown-out in 4/10 recoveries
assert [0, 1, 0, 0, 0, 0, ...] == [0, 0, 0, 0, 0, 0, ...]
  
  At index 1 diff: 1 != 0
  Use -v to get more diff
- test_BO04_random_brownouts_x10[3]  fail 3/3 — AssertionError: relay ON after brown-out in 1/10 recoveries
assert [0, 0, 0, 0, 0, 0, ...] == [0, 0, 0, 0, 0, 0, ...]
  
  At index 9 diff: 1 != 0
  Use -v to get more diff
- test_DI02_powerloss_leaves_old_or_new_valid_state  fail 3/3 — AssertionError: counter 4 -> 104: neither old nor a complete new state
assert 104 in (4, 5)
- test_DI03_interrupted_save_is_detected  fail 3/3 — AssertionError: no diagnostic about the interrupted save in the boot log
assert []
- test_DI04_power_cut_between_flash_writes[relay off-1]  fail 3/3 — AssertionError: mixed state after power cut: got (4, True), allowed old (3, True) or new (4, False)
assert (4, True) in ((3, True), (4, False))
- test_DI04_power_cut_between_flash_writes[relay on-1]  fail 3/3 — AssertionError: mixed state after power cut: got (4, False), allowed old (3, False) or new (4, True)
assert (4, False) in ((3, False), (4, True))
- test_DI05_corrupted_flash_is_detected[off-bit0]  fail 3/3 — AssertionError: corrupted flash switched the relay ON (saved state was OFF)
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7daf845f0>.relay
- test_DI05_corrupted_flash_is_detected[off-bit7]  fail 3/3 — AssertionError: corrupted flash switched the relay ON (saved state was OFF)
assert 1 == 0
 +  where 1 = relay()
 +    where relay = <dut.Device object at 0x7fc7daf848c0>.relay
- test_DI05_corrupted_flash_is_detected[on-bit0]  fail 3/3 — AssertionError: corruption not reported; device silently loaded counter=3 relay=False
assert []
- test_DI05_corrupted_flash_is_detected[on-bit7]  fail 3/3 — AssertionError: corruption not reported; device silently loaded counter=130 relay=True
assert []
- test_DI07_repeated_powerloss_x5  fail 3/3 — AssertionError: 5/5 interrupted saves left an invalid counter: [(2, 102), (104, 204), (206, 306), (308, 408), (410, 510)]
assert not [(2, 102), (104, 204), (206, 306), (308, 408), (410, 510)]
- test_NEG04_sensor_disconnected_after_recovery[brownout]  fail 3/3 — AssertionError: no explicit sensor error: ['[SENSOR] temp=0.0C humidity=0.0%']
assert False
 +  where False = any(<generator object test_NEG04_sensor_disconnected_after_recovery.<locals>.<genexpr> at 0x7fc7dad07ed0>)
- test_NEG04_sensor_disconnected_after_recovery[deep_sleep]  fail 3/3 — AssertionError: no explicit sensor error: ['[SENSOR] temp=0.0C humidity=0.0%']
assert False
 +  where False = any(<generator object test_NEG04_sensor_disconnected_after_recovery.<locals>.<genexpr> at 0x7fc7dad71150>)
- test_NEG04_sensor_disconnected_after_recovery[power_cycle]  fail 3/3 — AssertionError: no explicit sensor error: ['[SENSOR] temp=0.0C humidity=0.0%']
assert False
 +  where False = any(<generator object test_NEG04_sensor_disconnected_after_recovery.<locals>.<genexpr> at 0x7fc7dad705f0>)
- test_NEG04_sensor_disconnected_after_recovery[powerloss_cmd]  fail 3/3 — AssertionError: no explicit sensor error: ['[SENSOR] temp=0.0C humidity=0.0%']
assert False
 +  where False = any(<generator object test_NEG04_sensor_disconnected_after_recovery.<locals>.<genexpr> at 0x7fc7dad713c0>)
- test_NEG04_sensor_disconnected_after_recovery[wdt]  fail 3/3 — AssertionError: no explicit sensor error: ['[SENSOR] temp=0.0C humidity=0.0%']
assert False
 +  where False = any(<generator object test_NEG04_sensor_disconnected_after_recovery.<locals>.<genexpr> at 0x7fc7dad079f0>)
- test_SB01_sensor_failure_reported_explicitly[checksum_error]  fail 3/3 — AssertionError: invalid reading printed as a measurement: ['[SENSOR] temp=0.0C humidity=0.0%']
assert not True
 +  where True = any(<generator object test_SB01_sensor_failure_reported_explicitly.<locals>.<genexpr> at 0x7fc7dadad380>)
- test_SB01_sensor_failure_reported_explicitly[disconnected]  fail 3/3 — AssertionError: invalid reading printed as a measurement: ['[SENSOR] temp=0.0C humidity=0.0%']
assert not True
 +  where True = any(<generator object test_SB01_sensor_failure_reported_explicitly.<locals>.<genexpr> at 0x7fc7dadac660>)
- test_SB02_out_of_range_values_not_valid[hum_120pct]  fail 3/3 — AssertionError: out-of-range data reported as sensor_ok=true (25.0 C / 120.0 %)
assert True is False
- test_SB02_out_of_range_values_not_valid[temp_-60C]  fail 3/3 — AssertionError: out-of-range data reported as sensor_ok=true (-60.0 C / 50.0 %)
assert True is False
- test_SB02_out_of_range_values_not_valid[temp_150C]  fail 3/3 — AssertionError: out-of-range data reported as sensor_ok=true (150.0 C / 50.0 %)
assert True is False
- test_SB04_one_press_one_event[both_bounce]  fail 3/3 — AssertionError: 2 events for one press
assert (2 - 0) == 1
- test_SB04_one_press_one_event[release_bounce]  fail 3/3 — AssertionError: 2 events for one press
assert (2 - 0) == 1
- test_SB05_twenty_presses_twenty_events  fail 3/3 — AssertionError: 38 events for 20 presses
assert (38 - 0) == 20
- test_REC01_mixed_fault_storm_x20[11]  fail 3/3 — AssertionError: relay ON after 6 emergency resets: [('wdt', 'TASK_WDT', 106, 1), ('wdt', 'TASK_WDT', 107, 1), ('wdt', 'TASK_WDT', 315, 1), ('wdt', 'TASK_WDT', 315, 1), ('brownout', 'BROWNOUT', 315, 1), ('wdt', 'TASK_WDT', 319, 1)] | persistent counter jumped/rolled back 3x: [(4, 104), (107, 207), (207, 310)]
assert not ["relay ON after 6 emergency resets: [('wdt', 'TASK_WDT', 106, 1), ('wdt', 'TASK_WDT', 107, 1), ('wdt', 'TASK_WDT', 31...315, 1), ('wdt', 'TASK_WDT', 319, 1)]", 'persistent counter jumped/rolled back 3x: [(4, 104), (107, 207), (207, 310)]']
- test_REC01_mixed_fault_storm_x20[22]  fail 3/3 — AssertionError: relay ON after 5 emergency resets: [('brownout', 'BROWNOUT', 102, 1), ('brownout', 'BROWNOUT', 107, 1), ('brownout', 'BROWNOUT', 111, 1), ('wdt', 'TASK_WDT', 119, 1), ('wdt', 'TASK_WDT', 119, 1)] | persistent counter jumped/rolled back 3x: [(119, 219), (219, 320), (320, 422)]
assert not ["relay ON after 5 emergency resets: [('brownout', 'BROWNOUT', 102, 1), ('brownout', 'BROWNOUT', 107, 1), ('brownout',...9, 1), ('wdt', 'TASK_WDT', 119, 1)]", 'persistent counter jumped/rolled back 3x: [(119, 219), (219, 320), (320, 422)]']

## demo: 124 tests x 1 run(s) -> 121 passed, 3 failed

- test_SB02_out_of_range_values_not_valid[hum_120pct]  fail 1/1 — AssertionError: out-of-range data reported as sensor_ok=true (25.0 C / 120.0 %)
assert True is False
- test_SB02_out_of_range_values_not_valid[temp_-60C]  fail 1/1 — AssertionError: out-of-range data reported as sensor_ok=true (-60.0 C / 50.0 %)
assert True is False
- test_SB02_out_of_range_values_not_valid[temp_150C]  fail 1/1 — AssertionError: out-of-range data reported as sensor_ok=true (150.0 C / 50.0 %)
assert True is False
