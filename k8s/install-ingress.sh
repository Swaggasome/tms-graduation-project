#!/bin/bash

# 1. Устанавливаем cert-manager
echo "Установка cert-manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml

# 2. Устанавливаем NGINX Ingress Controller
echo "Установка NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

echo "Готово! Компоненты устанавливаются в фоне."
echo "Проверьте статус компонентов с помощью команд: 
kubectl get pods -n ingress-nginx 
kubectl get pods --namespace cert-manager