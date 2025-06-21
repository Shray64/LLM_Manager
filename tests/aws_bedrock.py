import boto3, json, os
from botocore.exceptions import ClientError

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-2",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

model_id = (
    "arn:aws:bedrock:us-east-2:931886963315:"
    "inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"
)

payload = {
    "anthropic_version": "bedrock-2023-05-31",   # required for Claude 4
    "max_tokens": 5000,
    "temperature": 1,
    "top_p": 0.95,
    "messages": [
        {"role": "user", "content": "Explain black holes to 8th-graders."}
    ],
    "thinking": {
        "type": "enabled",
        "budget_tokens": 4000
    }
}

try:
    # Use invoke_model instead of invoke_model_with_response_stream
    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )
    
    # Parse the response body
    response_body = json.loads(response['body'].read())
    
    # For Claude models, the response format is different from streaming
    if 'content' in response_body:
        # Extract the text from the content array
        for content_block in response_body['content']:
            if content_block.get('type') == 'text':
                print(content_block.get('text', ''))
    else:
        # Fallback in case the response format is different
        print(json.dumps(response_body, indent=2))

except ClientError as e:
    print("Bedrock error:", e.response["Error"]["Message"])
