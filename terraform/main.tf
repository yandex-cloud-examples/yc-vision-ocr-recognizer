variable "cloud_id" {
  type = string
}

variable "folder_id" {
  type = string
}

variable "zone" {
  type = string
}

locals {
  container_image  = "cr.yandex/sol/ml-ai/ocr-recognizer/ocr-recognizer:v1.0.0"
}

terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
    }
  }
}

provider "yandex" {
  zone      = var.zone
}

# Function Source
resource "random_string" "default" {
  length  = 4
  upper   = false
  lower   = true
  numeric = true
  special = false
}

# Service account main
resource "yandex_iam_service_account" "ocr-sa" {
  folder_id   = var.folder_id
  name        = "ocr-sa-${random_string.default.result}"
}

resource "yandex_resourcemanager_folder_iam_member" "ocr-sa-vision" {
  folder_id       = var.folder_id
  member          = "serviceAccount:${yandex_iam_service_account.ocr-sa.id}"
  role            = "ai.vision.user"
}

resource "yandex_resourcemanager_folder_iam_member" "ocr-sa-storage" {
  folder_id       = var.folder_id
  member          = "serviceAccount:${yandex_iam_service_account.ocr-sa.id}"
  role            = "storage.editor"
}

# Service account invoker
resource "yandex_iam_service_account" "ocr-sa-invoker" {
  folder_id   = var.folder_id
  name        = "ocr-sa-invoker-${random_string.default.result}"
}

resource "yandex_resourcemanager_folder_iam_member" "sa-invoker" {
  folder_id       = var.folder_id
  member          = "serviceAccount:${yandex_iam_service_account.ocr-sa-invoker.id}"
  role            = "serverless-containers.containerInvoker"
}

# API key
resource "yandex_iam_service_account_api_key" "sa-api-key" {
  service_account_id = yandex_iam_service_account.ocr-sa.id
  description        = "ocr-sa-${random_string.default.result} API key"
}

# Static access key
resource "yandex_iam_service_account_static_access_key" "sa-static-key" {
  service_account_id = yandex_iam_service_account.ocr-sa.id
  description        = "ocr-sa-${random_string.default.result} static key"
}

# Lockbox
resource "yandex_lockbox_secret" "secret-api" {
  name = "ocr-sa-api-${random_string.default.result}"
}

resource "yandex_lockbox_secret_version" "secret-api-v1" {
  secret_id = yandex_lockbox_secret.secret-api.id
  entries {
    key        = "secret_key"
    text_value = yandex_iam_service_account_api_key.sa-api-key.secret_key
  }
}

resource "yandex_lockbox_secret_iam_binding" "secret-api-viewer" {
  secret_id = yandex_lockbox_secret.secret-api.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.ocr-sa.id}"
  ]
}

# Bucket
resource "yandex_storage_bucket" "ocr-bucket" {
  access_key = yandex_iam_service_account_static_access_key.sa-static-key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
  bucket     = "ocr-recognition-${random_string.default.result}"

  depends_on = [yandex_resourcemanager_folder_iam_member.ocr-sa-storage]
}

# Object
resource "yandex_storage_object" "null-object" {
  access_key = yandex_iam_service_account_static_access_key.sa-static-key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
  bucket     = yandex_storage_bucket.ocr-bucket.id
  content = "." 
  key        = "input/"
}

# OCR
resource "yandex_serverless_container" "ocr" {
  name               = "ocr-recognizer-${random_string.default.result}"
  description        = "OCR recognition serverless container"
  memory             = 256
  cores              = 1
  execution_timeout  = "300s"
  service_account_id = yandex_iam_service_account.ocr-sa.id
  concurrency        = 5
  
  secrets {
    id                   = yandex_lockbox_secret.secret-api.id
    version_id           = yandex_lockbox_secret_version.secret-api-v1.id
    key                  = "secret_key"
    environment_variable = "API_KEY"
  }

  image {
    url = local.container_image
  }

  mounts {
    mount_point_path = "/bucket"
    mode             = "rw"
    object_storage {
      bucket = yandex_storage_bucket.ocr-bucket.id
    }
  }
}

# Triggers
resource "yandex_function_trigger" "ocr-timer" {
  name        = "ocr-timer-${random_string.default.result}"
  description = "Timer trigger for OCR processing"
  
  container {
    id                 = yandex_serverless_container.ocr.id
    service_account_id = yandex_iam_service_account.ocr-sa-invoker.id
    retry_attempts     = 1 
    retry_interval     = 30
  }
  
  timer {
    cron_expression = "* * * * ? *"
  }
}

resource "yandex_function_trigger" "ocr-bucket" {
  name        = "ocr-bucket-create-${random_string.default.result}"
  description = "Object storage trigger for OCR processing"
  
  container {
    id                 = yandex_serverless_container.ocr.id
    service_account_id = yandex_iam_service_account.ocr-sa-invoker.id
    retry_attempts     = 2
    retry_interval     = 10
  }
  
  object_storage {
    bucket_id    = yandex_storage_bucket.ocr-bucket.id
    batch_cutoff = 10
    prefix       = "input/"
    create       = true
    update       = false
    delete       = false
  }
}

output "bucket_id" {
  value = yandex_storage_bucket.ocr-bucket.id
}



