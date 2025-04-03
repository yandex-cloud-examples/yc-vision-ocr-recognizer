variable "folder_id" {
  description = "Yandex Cloud folder-id"
  type        = string
}

variable "cloud_id" {
  description = "Yandex Cloud cloud-id"
  type        = string
}

variable "zone" {
  description = "Yandex Cloud region"
  type        = string
  default     = "ru-central1-a"
}

variable "provider_key_file" {
  description = "Yandex Cloud provider key file"
  type        = string
  default     = "./key.json"
}

variable "container_image" {
  description = "OCR Recognizer container image"
  type        = string
  default     = "cr.yandex/sol/ml-ai/ocr-recognizer/ocr-recognizer:v1.0.0"
}
