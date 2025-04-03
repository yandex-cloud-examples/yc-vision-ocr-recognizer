# OCR Recognizer 

Данное решение позволяет получать изображения и PDF-документы из бакета [Object Storage](https://yandex.cloud/ru/services/storage), отправлять их на распознавание в сервис [Vision](https://yandex.cloud/ru/services/vision), а результаты распознавания сохранять обратно в [бакет](https://yandex.cloud/ru/docs/storage/concepts/bucket) Object Storage.

Скрипт написан на Python поэтому может быть легко разобран, доработан и оптимизирован под ваш сценарий.
<br><br>

## Процесс распознавания

<img src="docs/img/diag.jpg" width="600px" alt="Процесс распознавания изображений" />
<br><br>

1. Пользователь загружает изображения или документы в [поддерживаемых форматах](https://yandex.cloud/ru/docs/vision/concepts/ocr/#image-requirements) в бакет Object Storage, в директорию (префикс) `input`, которую нужно создать.

2. Скрипт получает файлы, созданные в директории `input` в бакете при помощи [триггера](https://yandex.cloud/ru/docs/serverless-containers/concepts/trigger/os-trigger) и отправляет на распознавание.

3. Файлы отправляются на распознавание, их `operation_id` сохраняется в директории `process`.

4. Скрипт запускается по таймеру, проверяет статус операций в директории `process`. В случае успешного завершения операции, результаты сохраняются в `result` в формате JSON и в формате TXT, а операция в `process` удаляется.

## Использование

Можно воспользоваться готовым [Terraform модулем](example/), который создает все необходимые ресурсы для начала обработки изображений и документов, а именно:
- Создает контейнер
- Создает триггеры
- Создает бакет
- Создает необходимые учетные записи и права

Будет создан бакет вида `ocr-recognition-xxx`, в котором нужно создать директорию `input` и загрузить туда PDF-документы или изображения.
Результат распознавания будет сохранен в тот же бакет, в директорию `result`.

### Локально

Скрипт может быть запущен локально:
```
python src/async_ocr_client.py --api-key xxx --image-path file.png
```

В результате будет возвращен `operation_id`, который можно использовать для получения результата:
```
python src/async_ocr_client.py --operation-id xxx --api-key yyy --output file.txt
```

Для того, чтобы создать API-ключ:
1) Необходимо [создать сервисную учетную запись](https://yandex.cloud/ru/docs/iam/operations/sa/create)
2) [Назначить роль](https://yandex.cloud/ru/docs/iam/operations/sa/assign-role-for-sa) `ai.vision.user`
3) [Создать API-ключ](https://yandex.cloud/ru/docs/iam/operations/authentication/manage-api-keys#create-api-key)