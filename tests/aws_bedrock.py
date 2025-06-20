# import boto3
# from botocore.exceptions import ClientError
# import os

# client = boto3.client("bedrock-runtime", 
#                       region_name="us-east-2",
#                       aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
#                       aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))

# model_id = (
#     "arn:aws:bedrock:us-east-2:931886963315:"
#     "inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"
# )


# user_message = "Describe the purpose of a 'hello world' program in one line."
# conversation = [
#     {
#         "role": "user",
#         "content": [{"text": user_message}],
#     }
# ]

# try:
#     # Send the message to the model, using a basic inference configuration.
#     response = client.converse(
#         modelId=model_id,
#         messages=conversation,
#         inferenceConfig={"maxTokens": 512, "temperature": 0.5, "topP": 0.9},
#     )

#     # Extract and print the response text.
#     response_text = response["output"]["message"]["content"][0]["text"]
#     print(response_text)

# except (ClientError, Exception) as e:
#     print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
#     exit(1)


import boto3, json, os
from botocore.exceptions import ClientError

bedrock = boto3.client(
    service_name="bedrock",
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
    "max_tokens": 1000,
    "temperature": 0.1,
    "top_p": 0.9,
    "messages": [
        {"role": "user", "content": "Explain black holes to 8th-graders."}
    ],
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
