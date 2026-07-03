# Random Baseline Strategy

## Зачем нужна стратегия

`random_baseline` — минимальная baseline-стратегия для smoke-тестирования executor на demo-счете.
Она позволяет быстро проверить сквозной путь: решение -> сигнал -> execution -> открытие/закрытие -> результат.

## Как работает

1. Каждые `decision_step_sec` секунд проверяет, можно ли принимать новое решение.
2. `should_decide()` вернет `True` только если:
   - нет открытой позиции;
   - нет активного ордера;
   - executor healthy;
   - market data свежие;
   - не активен cooldown;
   - прошел минимальный decision step.
3. `make_decision()` случайно выбирает сторону:
   - 50% `long`
   - 50% `short`
4. Создается `BaselineSignal` с TP/SL/timeout параметрами.
5. После закрытия позиции вызывается `on_position_closed()` и стартует cooldown.

## Параметры baseline v1

- `decision_step_sec = 30`
- `cooldown_sec = 20`
- `take_profit_ticks = 700`
- `stop_loss_ticks = 350`
- `timeout_sec = 300`
- `exit_market_fallback_enabled = True` — market reduce-only после неудачных maker-exit
- `exit_maker_max_attempts = 10`
- `exit_market_grace_sec = 60` — grace после `timeout_at`
- `shutdown_drain_sec = 25` — ожидание закрытия позиции при остановке процесса

Все параметры заданы в `strategy/random_baseline/config.py` (не через `.env`).

## Как расширять

- заменить random-решение на ML/правила без изменения внешнего контракта;
- добавить market filters (спред/волатильность/время);
- добавить более сложный risk manager до отправки сигнала в execution.
