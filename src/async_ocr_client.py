import grpc
import argparse
import os
import mimetypes
from yandex.cloud.ai.ocr.v1 import ocr_service_pb2_grpc
from yandex.cloud.ai.ocr.v1 import ocr_service_pb2

def recognize_text_async(image_path, api_key=None, max_file_size_mb=10):
    """
    Send an image for asynchronous text recognition and get the operation ID.
    
    Args:
        image_path: Path to the image file
        api_key: Optional API key for authentication
        max_file_size_mb: Maximum file size in MB (default: 10MB)
    
    Returns:
        Operation ID for the recognition request
        
    Raises:
        ValueError: If the file exceeds the maximum size limit or has an unsupported format
    """
    # Hardcoded API endpoint
    api_endpoint = "ocr.api.cloud.yandex.net:443"
    
    # Define supported file formats
    supported_mime_types = ['image/jpeg', 'image/png', 'application/pdf']
    supported_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
    
    # Check file extension
    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext not in supported_extensions:
        raise ValueError(f"Unsupported file format: {file_ext}. Supported formats are: JPEG, PNG, and PDF.")
    
    # Check file size before reading
    file_size_bytes = os.path.getsize(image_path)
    max_size_bytes = max_file_size_mb * 1024 * 1024  # Convert MB to bytes
    
    if file_size_bytes > max_size_bytes:
        raise ValueError(f"File size ({file_size_bytes / (1024 * 1024):.2f} MB) exceeds the maximum allowed size of {max_file_size_mb} MB")
    
    # Read the image file
    with open(image_path, 'rb') as f:
        image_content = f.read()
    
    # Determine mime type based on file extension
    mime_type = mimetypes.guess_type(image_path)[0]
    if not mime_type or mime_type not in supported_mime_types:
        # Try to infer from extension
        if file_ext == '.jpg' or file_ext == '.jpeg':
            mime_type = 'image/jpeg'
        elif file_ext == '.png':
            mime_type = 'image/png'
        elif file_ext == '.pdf':
            mime_type = 'application/pdf'
        else:
            raise ValueError(f"Could not determine MIME type for {image_path}. Supported formats are: JPEG, PNG, and PDF.")
    
    # Create secure gRPC channel for port 443
    if ':443' in api_endpoint:
        channel = grpc.secure_channel(api_endpoint, grpc.ssl_channel_credentials())
    else:
        channel = grpc.insecure_channel(api_endpoint)
    
    # Create metadata for authentication if API key is provided
    metadata = []
    if api_key:
        metadata.append(('authorization', f'Api-Key {api_key}'))
    
    # Create client stub
    stub = ocr_service_pb2_grpc.TextRecognitionAsyncServiceStub(channel)
    
    # Create recognition request
    request = ocr_service_pb2.RecognizeTextRequest(
        content=image_content,
        mime_type=mime_type,
        language_codes=['en', 'ru']  # Adjust based on languages in your image
    )
    
    # Send the request
    operation = stub.Recognize(request, metadata=metadata)
    
    # Return the operation ID
    return operation.id

def get_recognition_results(operation_id, api_key=None):
    """
    Retrieve the results of an asynchronous OCR operation.
    
    Args:
        operation_id: The ID of the operation to retrieve results for
        api_key: Optional API key for authentication
    
    Returns:
        List of recognition results
    """
    # Hardcoded API endpoint
    api_endpoint = "ocr.api.cloud.yandex.net:443"
    # Create secure gRPC channel for port 443
    if ':443' in api_endpoint:
        channel = grpc.secure_channel(api_endpoint, grpc.ssl_channel_credentials())
    else:
        channel = grpc.insecure_channel(api_endpoint)
    
    # Create metadata for authentication if API key is provided
    metadata = []
    if api_key:
        metadata.append(('authorization', f'Api-Key {api_key}'))
    
    # Create client stub
    stub = ocr_service_pb2_grpc.TextRecognitionAsyncServiceStub(channel)
    
    # Create request to get recognition results
    request = ocr_service_pb2.GetRecognitionRequest(
        operation_id=operation_id
    )
    
    # Get the results
    results = []
    try:
        for response in stub.GetRecognition(request, metadata=metadata):
            results.append(response)
    except grpc.RpcError as e:
        print(f"RPC error: {e.code()}, {e.details()}")
        raise
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Asynchronous OCR using Yandex Cloud')
    parser.add_argument('--image-path', help='Path to the image file')
    parser.add_argument('--operation-id', help='Operation ID to retrieve results for')
    parser.add_argument('--api-key', help='Yandex Cloud API key')
    parser.add_argument('--output', help='Path to save the recognition results')
    
    args = parser.parse_args()
    
    if not args.image_path and not args.operation_id:
        parser.error("Either --image-path or --operation-id must be provided")
    
    try:
        if args.image_path:
            # Submit new recognition request
            operation_id = recognize_text_async(args.image_path, args.api_key)
            print(f"Recognition request submitted successfully!")
            print(f"Operation ID: {operation_id}")
            print(f"You can use this ID to retrieve the recognition results later with:")
            print(f"python {os.path.basename(__file__)} --operation-id {operation_id}" + 
                  (f" --api-key YOUR_API_KEY" if args.api_key else ""))
        
        if args.operation_id:
            # Retrieve results for an existing operation
            print(f"Retrieving results for operation: {args.operation_id}")
            results = get_recognition_results(args.operation_id, args.api_key)
            
            if not results:
                print("No results returned. The operation may still be in progress.")
            else:
                print(f"Retrieved {len(results)} result(s).")
                
                for i, result in enumerate(results):
                    if result.text_annotation.full_text:
                        print(f"\nPage {result.page or i+1} text:")
                        print(result.text_annotation.full_text[:500] + 
                              ("..." if len(result.text_annotation.full_text) > 500 else ""))
                    
                    if args.output:
                        output_file = f"{args.output}_{i}.txt" if len(results) > 1 else args.output
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(result.text_annotation.full_text)
                        print(f"Full text saved to {output_file}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
