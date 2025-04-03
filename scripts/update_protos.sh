#!/bin/bash
# Script to update protobuf generated files for the OCR service

set -e

echo "Starting protobuf files update process..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Clone the Yandex Cloud API repository
echo "Cloning Yandex Cloud API repository..."
git clone https://github.com/yandex-cloud/cloudapi

# Install required tools if not already installed
pip install grpcio-tools

# Create output directory
cd cloudapi
mkdir -p output

# Generate Python code from proto files
echo "Generating Python code from proto files..."
python3 -m grpc_tools.protoc -I . -I third_party/googleapis --python_out=output \
  --grpc_python_out=output \
  google/api/http.proto \
  google/api/annotations.proto \
  yandex/cloud/api/operation.proto \
  google/rpc/status.proto \
  yandex/cloud/operation/operation.proto \
  yandex/cloud/validation.proto \
  yandex/cloud/ai/ocr/v1/ocr.proto \
  yandex/cloud/ai/ocr/v1/ocr_service.proto

# Copy generated files to the project
echo "Copying generated files to the project..."
PROJECT_ROOT=$(cd ../../.. && pwd)  # Adjust this path as needed to point to your project root
cp -r output/google $PROJECT_ROOT/src/
cp -r output/yandex $PROJECT_ROOT/src/

echo "Cleaning up temporary files..."
cd ../../
rm -rf $TEMP_DIR

echo "Protobuf files update completed successfully!"
