# resume/

Профільні матеріали для співбесіди на Embedded QA. Кожна навичка підкріплена посиланням на конкретний артефакт цього портфоліо, а не перелічена як «знаю інструмент».

> CV у PDF додається сюди окремо (`CV_Lakhno_Embedded_QA.pdf`).

## Навички, продемонстровані в портфоліо

| Навичка | Де видно | Результат |
|---|---|---|
| Risk-based test strategy, Master Test Plan | [master-test-plan.md](../master-test-plan.md), [risk-matrix](../docs/risk-matrix.md) | 13 ризиків (Ймовірність × Вплив), перегляд «до / після», ланцюги ризиків |
| Black-box тест-дизайн: state transition, BVA, timing, negative, combination | [test-matrix](../docs/test-matrix.md), [wokwi/smart_gate](../wokwi/smart_gate/) | Таймаут лише в одному напрямку знайдено межами 9.9 / 10.0 / >10 с |
| Protocol analysis (I2C), logic analyzer, PulseView / sigrok | [pulseview/](../pulseview/) | Відрізнив зависання прошивки від lock-up шини за trace |
| GPIO, переривання, debounce, Wokwi CI scenarios | [pulseview/gpio_debounce](../pulseview/gpio_debounce/), [wokwi/debounce_scenarios](../wokwi/debounce_scenarios/) | Фактичний поріг фільтра ≈1 мс замість 30 мс |
| UART / CLI boundary і stress testing | [uart-cli/](../uart-cli/) | Межа 40/41 символ → reboot і виконання хвоста рядка |
| Fault injection і recovery: WDT, brown-out, power cut, NVS | [pytest/w5_recovery](../pytest/w5_recovery/) | Реле ON через ≈340 мс після WDT reset, 10/10 |
| IoT network: reconnect, offline buffer, duplicates, memory stability | [network-stress/](../network-stress/) | Тиха втрата 92 зі 100 повідомлень; витік 64 B / повідомлення |
| Python / pytest автоматизація, parametrize, контроль на еталоні, JUnit | [pytest/](../pytest/) | 207 автотестів, кожен FAIL 3/3 |
| Bug reporting з evidence | [bug-reports/](../bug-reports/) | 35 дефектів, 9 повних release-blocking reports |
| Release decision за evidence | [release-decision](../docs/release-decision.md) | NO-GO при 67 % PASS з вимірюваними умовами переходу |

## 90-секундна історія проєкту

Див. [docs/defense-brief.md](../docs/defense-brief.md): Product → Risk → Strategy → Evidence → Finding → Decision.
