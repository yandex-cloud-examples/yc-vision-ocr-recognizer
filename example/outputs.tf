output "ocr_bucket_id" {
  description = "OCR Bucket"
  value       = try(module.ocr.bucket_id, null)
}
