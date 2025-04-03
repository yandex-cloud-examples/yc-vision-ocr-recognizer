import os
import json
import time
import glob
import sys
import logging
from bottle import Bottle, request, response
from google.protobuf.json_format import MessageToDict
from async_ocr_client import recognize_text_async, get_recognition_results

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('ocr-service')

# Create Bottle app
app = Bottle()

@app.post('/')
def process_ocr():
    # Get the request data
    event = request.json
    logger.info(f"Received event: {json.dumps(event)[:200]}...")  # Log truncated event data
    
    # Get API key from environment variable (should be configured in your function)
    api_key = os.environ.get('API_KEY')
    if not api_key:
        logger.error("API_KEY environment variable not set")
    
    results = []
    
    # Check the event type from the first message
    if event.get('messages') and len(event.get('messages')) > 0:
        event_type = event['messages'][0].get('event_metadata', {}).get('event_type', '')
        logger.info(f"Processing event type: {event_type}")
        
        # Handle timer events - process pending OCR operations
        if event_type == 'yandex.cloud.events.serverless.triggers.TimerMessage':
            process_dir = "/bucket/process"
            results_dir = "/bucket/results"
            
            # Create results directory if it doesn't exist
            os.makedirs(results_dir, exist_ok=True)
            
            # List all operation files in the process directory
            operation_files = glob.glob(f"{process_dir}/*")
            logger.info(f"Found {len(operation_files)} pending operations to process")
            
            for operation_file in operation_files:
                try:
                    # Get operation ID from filename
                    operation_id = os.path.basename(operation_file)
                    logger.info(f"Processing operation: {operation_id}")
                    
                    # Read operation data
                    with open(operation_file, 'r') as f:
                        operation_data = json.loads(f.read())
                    
                    # Get recognition results
                    logger.info(f"Checking results for operation: {operation_id}")
                    ocr_results = get_recognition_results(operation_id, api_key)
                    
                    if ocr_results:
                        # Update operation status to done
                        operation_data['done'] = True
                        operation_data['last_updated'] = time.time()
                        
                        # Save OCR results
                        object_filename = os.path.basename(operation_data['object_id'])
                        result_filename = f"{results_dir}/{object_filename}.txt"
                        json_filename = f"{results_dir}/{object_filename}.json"
                        logger.info(f"Writing results to: {result_filename} and {json_filename}")

                        try:
                            # Extract text from OCR results and write to file
                            with open(result_filename, 'w', encoding='utf-8') as f:
                                # Try different approaches based on what ocr_results actually is
                                if hasattr(ocr_results, '__iter__'):
                                    logger.info("OCR results is iterable")
                                    for i, result in enumerate(ocr_results):
                                        logger.info(f"Processing result {i}")
                                        if hasattr(result, 'text_annotation') and hasattr(result.text_annotation, 'full_text'):
                                            if result.text_annotation.full_text:
                                                # Add page number if there are multiple pages
                                                if len(ocr_results) > 1:
                                                    f.write(f"--- Page {getattr(result, 'page', i+1)} ---\n")
                                                f.write(result.text_annotation.full_text)
                                                f.write("\n\n")  # Add spacing between pages
                                elif hasattr(ocr_results, 'text_annotation') and hasattr(ocr_results.text_annotation, 'full_text'):
                                    logger.info("OCR results is a single result object")
                                    f.write(ocr_results.text_annotation.full_text)
                                else:
                                    logger.info("OCR results has unknown format, writing as string")
                                    f.write(str(ocr_results))
                            
                            # Also save the full OCR results as JSON
                            with open(json_filename, 'w', encoding='utf-8') as f:
                                # Convert OCR results to a serializable format using MessageToDict
                                if hasattr(ocr_results, '__iter__'):
                                    # Handle multiple results (e.g., multiple pages)
                                    json_results = [MessageToDict(result) for result in ocr_results]
                                else:
                                    # Handle single result object
                                    json_results = MessageToDict(ocr_results)
                                    
                                # Write the JSON file
                                json.dump(json_results, f, ensure_ascii=False, indent=2)
                                logger.info(f"Successfully wrote JSON results to {json_filename}")
                        except Exception as e:
                            logger.error(f"Error writing OCR results: {e}", exc_info=True)

                        logger.info("OCR processing completed")

                        # Delete the operation file
                        os.remove(operation_file)
                        logger.info(f"Deleted operation file: {operation_file}")
                        
                        result_info = {
                            'operation_id': operation_id,
                            'status': 'completed',
                            'saved_to': result_filename,
                            'json_results': json_filename
                        }
                        logger.info(f"Operation completed: {json.dumps(result_info)}")
                        results.append(result_info)
                    else:
                        # Operation still in progress, update last_checked time
                        operation_data['last_updated'] = time.time()
                        with open(operation_file, 'w') as f:
                            f.write(json.dumps(operation_data))
                        
                        result_info = {
                            'operation_id': operation_id,
                            'status': 'in_progress'
                        }
                        logger.info(f"Operation in progress: {json.dumps(result_info)}")
                        results.append(result_info)
                        
                except Exception as e:
                    error_info = {
                        'operation_id': os.path.basename(operation_file) if 'operation_file' in locals() else 'unknown',
                        'error': str(e)
                    }
                    logger.error(f"Error processing operation: {json.dumps(error_info)}", exc_info=True)
                    results.append(error_info)
            
            return {
                'message': 'Processed pending OCR operations',
                'results': results
            }
            
        # Handle object creation events - submit new OCR requests
        elif event_type == 'yandex.cloud.events.storage.ObjectCreate':
            # Process each message in the event
            message_count = len(event.get('messages', []))
            logger.info(f"Processing {message_count} object creation messages")
            for message in event.get('messages', []):
                try:
                    # Extract bucket_id and object_id from the message
                    bucket_id = message['details']['bucket_id']
                    object_id = message['details']['object_id']
                    logger.info(f"Processing new object: {object_id} in bucket: {bucket_id}")
                    
                    # Construct the path to the image file in the mounted bucket
                    image_path = f"/bucket/{object_id}"

                    # Call the OCR service to start recognition
                    logger.info(f"Submitting OCR request for: {image_path}")
                    operation_id = recognize_text_async(image_path, api_key)
                    logger.info(f"Received operation ID: {operation_id}")
                    
                    # Create the process directory if it doesn't exist
                    process_dir = f"/bucket/process"
                    os.makedirs(process_dir, exist_ok=True)
                    
                    # Save the operation ID to a file in the process directory
                    result_path = f"{process_dir}/{operation_id}"
                    with open(result_path, 'w') as f:
                        result_data = {
                            'done': False,
                            'last_updated': time.time(),
                            'bucket_id': bucket_id,
                            'object_id': object_id
                        }
                        f.write(json.dumps(result_data))
                    logger.info(f"Saved operation data to: {result_path}")
                    
                    results.append({
                        'bucket_id': bucket_id,
                        'object_id': object_id,
                        'operation_id': operation_id,
                        'status': 'submitted'
                    })
                    
                except ValueError as e:
                    if "exceeds the maximum allowed size" in str(e):
                        error_info = {
                            'bucket_id': bucket_id,
                            'object_id': object_id,
                            'error': str(e),
                            'status': 'rejected_file_too_large'
                        }
                        logger.error(f"File too large: {json.dumps(error_info)}")
                        results.append(error_info)
                    elif "Unsupported file format" in str(e) or "Could not determine MIME type" in str(e):
                        error_info = {
                            'bucket_id': bucket_id,
                            'object_id': object_id,
                            'error': str(e),
                            'status': 'rejected_unsupported_format'
                        }
                        logger.error(f"Unsupported file format: {json.dumps(error_info)}")
                        results.append(error_info)
                    else:
                        error_info = {
                            'bucket_id': bucket_id,
                            'object_id': object_id,
                            'error': str(e),
                            'status': 'rejected_value_error'
                        }
                        logger.error(f"Value error: {json.dumps(error_info)}")
                        results.append(error_info)
                except Exception as e:
                    error_info = {
                        'error': str(e),
                        'message': message,
                        'status': 'rejected_other_error'
                    }
                    logger.error(f"Error processing message: {json.dumps(error_info)}", exc_info=True)
                    results.append(error_info)
    
    # Bottle automatically converts dictionaries to JSON
    return {
        'message': 'OCR recognition tasks submitted',
        'results': results
    }

# Add a health check endpoint
@app.get('/health')
def health_check():
    logger.info("Health check requested")
    return {'status': 'ok'}

# Run the Bottle app
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting OCR service on port {port}")
    # Run in quiet mode to suppress server startup messages
    app.run(host='0.0.0.0', port=port, quiet=True)
