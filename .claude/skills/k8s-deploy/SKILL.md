---
name: k8s-deploy
description: OpenShift（Kubernetes）へのデプロイ。マニフェストの更新、ビルド実行、デプロイ手順の実施時に使用する。「デプロイ」「OpenShift」「Kubernetes」「k8s」「oc」「マニフェスト」「Route」「BuildConfig」に関するタスクで発動する。
---

# OpenShiftデプロイ

## 概要

`k8s/` ディレクトリにKustomize対応のOpenShiftマニフェストを配置。`oc apply -k` で一括適用可能。

## マニフェスト構成

| ファイル | リソース | 用途 |
|---|---|---|
| namespace.yaml | Namespace | `equipment-detector` 名前空間 |
| imagestream.yaml | ImageStream | コンテナイメージ管理 |
| buildconfig.yaml | BuildConfig | Gitからのコンテナビルド |
| pvc.yaml | PVC | SQLiteデータ永続化（1Gi, ReadWriteOnce） |
| deployment.yaml | Deployment | アプリ本体（Recreate戦略） |
| service.yaml | Service | 内部通信（port 80, 8000） |
| route.yaml | Route | 外部公開（TLS edge termination） |

## デプロイ手順

```bash
# 1. 全リソース一括適用
oc apply -k k8s/

# 2. ビルド実行（初回 or コード更新時）
oc start-build equipment-detector-build -n equipment-detector --follow

# 3. デプロイ状況確認
oc get pods -n equipment-detector
oc logs -f deployment/equipment-detector -n equipment-detector
```

## 注意事項

- **Recreate戦略**: SQLiteは同時アクセス不可のため、RollingUpdateではなくRecreateを使用
- **PVC**: SQLiteファイルはPVCにマウント（`/app/data`）。Podが再起動してもデータは永続化
- **buildconfig.yaml**: `spec.source.git.uri` を実際のリポジトリURLに変更すること
- **イメージレジストリ**: OpenShift内部レジストリ（`image-registry.openshift-image-registry.svc:5000`）を使用
- ヘルスチェック: `GET /api/health`（liveness: 30秒間隔、readiness: 10秒間隔）
