module "ocr" {
  source = "../terraform/"

  folder_id         = var.folder_id
  cloud_id          = var.cloud_id
}