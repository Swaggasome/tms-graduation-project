# SmartMeeting

Web-система бронирования переговорных комнат в офисе.

Проект реализует календарь занятости ресурсов с запретом двойного бронирования, асинхронные задачи через Celery/Redis и экспорт событий в `.ics` для импорта во внешние календари.

## Стек

- Python / Django 4.2
- PostgreSQL 15
- Redis 7
- Celery / Celery Beat
- Gunicorn
- Docker / Docker Compose
- Kubernetes
- Kustomize
- Yandex Cloud Managed Kubernetes
- Yandex Container Registry
- cert-manager
- ingress-nginx

## Структура репозитория

```text
.
├── .github/workflows/deploy.yaml      # CI/CD workflow для сборки и деплоя
├── Dockerfile                         # Docker-образ приложения
├── docker-compose.yml                 # Локальное окружение
├── k8s/
│   ├── base/                          # Базовые Kubernetes-манифесты
│   ├── cluster/                       # Кластерные ресурсы: ClusterIssuer
│   └── overlays/
│       ├── staging/                   # Staging overlay
│       ├── production/                # Production overlay
│       └── feature/                   # Feature overlay
├── manage.py
└── requirements.txt
```

## Локальный запуск через Docker Compose

### 1. Поднять окружение

```bash
docker compose up --build
```

Будут запущены:

- `web` — Django-приложение на порту `8000`;
- `postgres` — база данных PostgreSQL на порту `5432`;
- `redis` — Redis на порту `6379`;
- `celery` — Celery worker;
- `celery-beat` — планировщик периодических задач.

### 2. Выполнить миграции

```bash
docker compose exec web python manage.py migrate
```

### 3. Создать переговорные комнаты

```bash
docker compose exec web python manage.py create_rooms
```

### 4. Настроить расписание напоминаний

```bash
docker compose exec web python manage.py setup_reminder_schedule
```

### 5. Создать администратора

```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Открыть приложение

```text
http://localhost:8000
```

## CI/CD

Деплой выполняется GitHub Actions workflow:

```text
.github/workflows/deploy.yaml
```

Workflow запускается при push в ветки:

```text
main
staging
feature/**
```

Логика окружений:

| Ветка | Окружение | Namespace | Overlay |
|---|---|---|---|
| `main` | production | `smartmeeting-prod` | `k8s/overlays/production` |
| `staging` | staging | `smartmeeting-staging` | `k8s/overlays/staging` |
| `feature/**` | feature | генерируется из имени ветки | `k8s/overlays/feature` |

Workflow выполняет:

1. Сборку Docker-образа.
2. Push образа в Yandex Container Registry.
3. Аутентификацию в Yandex Cloud.
4. Получение kubeconfig для Managed Kubernetes.
5. Установку `cert-manager`.
6. Установку `ingress-nginx`.
7. Применение кластерных ресурсов из `k8s/cluster`.
8. Создание namespace.
9. Генерацию Kubernetes Secret из GitHub Secrets.
10. Подготовку overlay через Kustomize.
11. Деплой приложения в Kubernetes.
12. Проверку rollout статуса deployment-ов.

## GitHub Secrets

В репозитории должны быть настроены следующие secrets.

### Yandex Cloud / Container Registry

| Secret | Описание |
|---|---|
| `YC_SA_JSON_CREDENTIALS` | JSON-ключ сервисного аккаунта Yandex Cloud |
| `YC_CLOUD_ID` | ID облака |
| `YC_FOLDER_ID` | ID каталога |
| `YC_K8S_CLUSTER_NAME` | ID или имя Managed Kubernetes кластера |
| `CR_REGISTRY_ID` | ID Yandex Container Registry |
| `CR_REPOSITORY` | Имя репозитория образа, например `smartmeeting` |

Рекомендуется указывать в `YC_K8S_CLUSTER_NAME` именно ID кластера, а не имя.

### Домены и TLS

| Secret | Пример |
|---|---|
| `CERT_MANAGER_EMAIL` | `admin@example.com` |
| `PROD_APP_DOMAIN` | `smartmeeting-app.ru` |
| `STAGING_APP_DOMAIN` | `staging.smartmeeting-app.ru` |

`CERT_MANAGER_EMAIL` используется для Let's Encrypt ClusterIssuer.

`PROD_APP_DOMAIN` и `STAGING_APP_DOMAIN` используются для Ingress host и Django CSRF trusted origins.

### Production Django / DB / S3

| Secret | Описание |
|---|---|
| `PROD_DB_USER` | Пользователь PostgreSQL |
| `PROD_DB_PASSWORD` | Пароль PostgreSQL |
| `PROD_DB_DATABASE` | Имя БД |
| `PROD_DJANGO_SECRET_KEY` | Django secret key |
| `EMAIL_HOST_USER` | Пользователь SMTP |
| `EMAIL_HOST_PASSWORD` | Пароль SMTP |
| `YC_STORAGE_BUCKET_NAME` | Имя Object Storage bucket |
| `YC_STORAGE_ACCESS_KEY` | Static access key |
| `YC_STORAGE_SECRET_KEY` | Static secret key |

### Staging / Feature

| Secret | Описание |
|---|---|
| `STAGING_DB_USER` | Пользователь PostgreSQL |
| `STAGING_DB_PASSWORD` | Пароль PostgreSQL |
| `STAGING_DB_DATABASE` | Имя БД |
| `STAGING_DJANGO_SECRET_KEY` | Django secret key |

Feature-окружения используют staging-настройки БД и домена, если в workflow не задана отдельная логика.

## Инфраструктура

Terraform-код инфраструктуры находится в отдельном репозитории:

```text
https://github.com/Swaggasome/tms-graduation-project-infra.git
```

После применения Terraform нужно получить значения outputs и добавить их в GitHub Secrets.

Пример получения JSON-ключа сервисного аккаунта:

```bash
terraform output -raw yc_sa_json_credentials_raw > key.json
```

Значение файла `key.json` нужно сохранить в GitHub Secret:

```text
YC_SA_JSON_CREDENTIALS
```

После сохранения секрета локальный файл с ключом нужно удалить:

```bash
rm -f key.json
```

## Ручная проверка доступа к Kubernetes

Перед запуском workflow можно локально проверить, что кластер доступен:

```bash
yc config set cloud-id <YC_CLOUD_ID>
yc config set folder-id <YC_FOLDER_ID>
yc config set service-account-key key.json

yc managed-kubernetes cluster list --folder-id <YC_FOLDER_ID>
```

Получить kubeconfig:

```bash
yc managed-kubernetes cluster get-credentials <YC_K8S_CLUSTER_NAME> \
  --folder-id <YC_FOLDER_ID> \
  --external
```

Если возникает ошибка:

```text
cluster with id or name "..." not found
```

проверьте:

- правильность `YC_K8S_CLUSTER_NAME`;
- правильность `YC_FOLDER_ID`;
- права сервисного аккаунта;
- что кластер находится именно в указанном каталоге.

## Ручная установка кластерных компонентов

Workflow делает это автоматически, но вручную команды выглядят так:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.19.5/cert-manager.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

Проверка:

```bash
kubectl get pods -n cert-manager
kubectl get pods -n ingress-nginx
```

Применение кластерных ресурсов:

```bash
export CERT_MANAGER_EMAIL=admin@example.com
cp -r k8s/cluster /tmp/k8s-cluster
envsubst < k8s/cluster/cluster-issuers.yaml > /tmp/k8s-cluster/cluster-issuers.yaml
kubectl apply -k /tmp/k8s-cluster
```

## DNS

После установки `ingress-nginx` получите внешний IP LoadBalancer:

```bash
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Создайте DNS A-записи:

```text
<PROD_APP_DOMAIN>      A    <INGRESS_EXTERNAL_IP>
<STAGING_APP_DOMAIN>   A    <INGRESS_EXTERNAL_IP>
```

Пример:

```text
smartmeeting-app.ru           A    158.160.XX.XX
staging.smartmeeting-app.ru   A    158.160.XX.XX
```

## Kubernetes deploy вручную

Обычно деплой выполняется GitHub Actions. Для ручной проверки можно использовать Kustomize.

### Staging

```bash
export APP_DOMAIN=staging.smartmeeting-app.ru
export IMAGE_NAME=cr.yandex/<CR_REGISTRY_ID>/smartmeeting
export IMAGE_TAG=<TAG>

cp -r k8s/overlays/staging /tmp/smartmeeting-staging

for file in /tmp/smartmeeting-staging/ingress-patch.yaml /tmp/smartmeeting-staging/configmap-patch.yaml; do
  envsubst < "$file" > "$file.tmp"
  mv "$file.tmp" "$file"
done

cd /tmp/smartmeeting-staging
kustomize edit set namespace smartmeeting-staging
kustomize edit set image smartmeeting-app="$IMAGE_NAME:$IMAGE_TAG"
kubectl apply -k .
```

### Production

```bash
export APP_DOMAIN=smartmeeting-app.ru
export IMAGE_NAME=cr.yandex/<CR_REGISTRY_ID>/smartmeeting
export IMAGE_TAG=<TAG>

cp -r k8s/overlays/production /tmp/smartmeeting-production

for file in /tmp/smartmeeting-production/ingress-patch.yaml /tmp/smartmeeting-production/configmap-patch.yaml; do
  envsubst < "$file" > "$file.tmp"
  mv "$file.tmp" "$file"
done

cd /tmp/smartmeeting-production
kustomize edit set namespace smartmeeting-prod
kustomize edit set image smartmeeting-app="$IMAGE_NAME:$IMAGE_TAG"
kubectl apply -k .
```

## Проверка после деплоя

Проверить pods:

```bash
kubectl get pods -n smartmeeting-staging
kubectl get pods -n smartmeeting-prod
```

Проверить deployments:

```bash
kubectl rollout status deployment/web -n smartmeeting-staging
kubectl rollout status deployment/celery-worker -n smartmeeting-staging
kubectl rollout status deployment/celery-beat -n smartmeeting-staging
```

Проверить ingress:

```bash
kubectl get ingress -A
```

Проверить сертификаты:

```bash
kubectl get certificate -A
kubectl get challenge -A
kubectl get order -A
```

Посмотреть логи web:

```bash
kubectl logs -n smartmeeting-staging deployment/web
```

Создать администратора в Kubernetes:

```bash
kubectl -n smartmeeting-staging exec -it deployment/web -- python manage.py createsuperuser
```

## Типовые проблемы

### `cluster with id or name "..." not found`

Причина: неправильный `YC_K8S_CLUSTER_NAME`, неправильный `YC_FOLDER_ID` или у сервисного аккаунта нет доступа к кластеру.

Проверка:

```bash
yc managed-kubernetes cluster list --folder-id <YC_FOLDER_ID>
```

### Сертификат не выпускается

Проверить:

```bash
kubectl describe certificate -A
kubectl describe challenge -A
kubectl logs -n cert-manager deployment/cert-manager
```

Также убедиться, что DNS A-запись домена указывает на внешний IP `ingress-nginx-controller`.

### Образ не обновился

Проверить итоговый image в deployment:

```bash
kubectl get deployment web -n smartmeeting-staging -o jsonpath='{.spec.template.spec.containers[0].image}'
```

В манифестах базовый image должен быть:

```yaml
image: smartmeeting-app
```

А workflow должен выполнять:

```bash
kustomize edit set image smartmeeting-app="$IMAGE_NAME:$IMAGE_TAG"
```

### Не применились домены в overlay

Проверить, что в GitHub Secrets заданы:

```text
PROD_APP_DOMAIN
STAGING_APP_DOMAIN
```

И что перед `kubectl apply -k` выполняется `envsubst` для файлов:

```text
ingress-patch.yaml
configmap-patch.yaml
```
