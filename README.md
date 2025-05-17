# Haier EVO Fridge Integration for Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs) [![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)

Неофициальная интеграция для работы с холодильниками [Haier Evo](https://haieronline.ru/evo-iot/) (RU, KZ, BY).

Бета-версия: может работать некорректно.

## Поддерживаемые устройства
Ниже приведен список устройств, работа с которыми была **проверена пользователями**. Если ваше устройство поддерживается, но отсутствует в списке - сообщите в [Issues](https://github.com/borolis/haier-evo-fridge-ha-integration/issues) об этом.

#### Холодильники
- BCF3261WRU

## Функциональность
- Управление температурой холодильной камеры
- Управление температурой морозильной камеры
- Режим "Отпуск"
- Режим "Супер-охлаждение"
- Режим "Супер-заморозка"
- Отслеживание состояния двери

## Установка

1. Установите HACS (Home Assistant Community Store)
2. Добавьте этот репозиторий в HACS как пользовательский
3. Установите интеграцию через HACS
4. Перезапустите Home Assistant
5. Добавьте интеграцию через интерфейс Home Assistant (Настройки -> Устройства и службы -> Добавить интеграцию -> Haier EVO Fridge)

## Отладка

Для включения подробного логирования добавьте в configuration.yaml:

```yaml
logger:
  default: info
  logs:
    custom_components.haier_evo_fridge: debug
```
## Совместимость
Haier предлагает разные мобильные приложения для разных рынков и стран. Эта интеграция поддерживает только устройства, которыми можно управлять через приложение [Evo](https://haieronline.ru/evo-iot/). Загрузите приложение Evo и проверьте совместимость с вашим устройством.

| Приложение      | Рынок         | Совместимость                           | Альтернатива                                                                    |
|-----------------|---------------|-----------------------------------------|----------------------------------------------------------------------------------|
| Haier Evo       | Россия        | :heavy_check_mark:                      |                                                                                 |
| Haier hOn       | Европа        | :x:                                     | [Andre0512/hon](https://github.com/Andre0512/hon)                               |
