# Updating Protobuf Generated Files

This document describes the process for updating the protobuf generated files used in this project.

## Background

The `src/google` and `src/yandex` directories contain generated Python code from protobuf definitions. These files are used for communication with Yandex Cloud OCR services.

## Update Process

You can update these files using either the automated script or by following the manual process.

### Option 1: Using the Automated Script

We provide a script that automates the entire process:

```bash
# Make the script executable first
chmod +x scripts/update_protos.sh

# Run the script
./scripts/update_protos.sh
```

### Option 2: Manual Process

If you prefer to update the files manually, follow these steps:

1. Clone the Yandex Cloud API repository:
   ```bash
   git clone https://github.com/yandex-cloud/cloudapi
   ```

2. Install the required tools:
   ```bash
   pip install grpcio-tools
   ```

3. Generate the Python code:
   ```bash
   cd cloudapi
   mkdir output
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
   ```

4. Copy the generated files to your project:
   ```bash
   cp -r output/google /path/to/your/project/src/
   cp -r output/yandex /path/to/your/project/src/
   ```

## Verification

After updating the protobuf files, you should verify that your application still works correctly with the new files. Run your tests or manually test the OCR functionality to ensure everything is working as expected.

## Troubleshooting

If you encounter issues after updating the protobuf files:

1. Check that all required files were generated and copied correctly
2. Verify that the versions of grpcio and grpcio-tools are compatible with your project
3. Look for any API changes in the Yandex Cloud documentation that might require code updates
