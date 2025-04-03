module "ocr" {
  source = "github.com/yandex-cloud-examples/yc-vision-ocr-recognizer/terraform"
  
  folder_id         = var.folder_id
  cloud_id          = var.cloud_id
}