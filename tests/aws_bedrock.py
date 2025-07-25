# import boto3, json, os
# from botocore.exceptions import ClientError

# bedrock = boto3.client(
#     service_name="bedrock-runtime",
#     region_name="us-east-2",
#     aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
#     aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
# )

# model_id = (
#     "arn:aws:bedrock:us-east-2:931886963315:"
#     "inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"
# )

# payload = {
#     "anthropic_version": "bedrock-2023-05-31",   # required for Claude 4
#     "max_tokens": 64000,
#     "temperature": 1,
#     # "top_p": 0.95,
#     "messages": [
#         {"role": "user", "content": "Explain black holes to 8th-graders."}
#     ],
#     "thinking": {
#         "type": "enabled",
#         "budget_tokens": 32000
#     }
# }

# try:
#     # Use invoke_model instead of invoke_model_with_response_stream
#     response = bedrock.invoke_model(
#         modelId="arn:aws:bedrock:us-east-2:931886963315:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
#         body=json.dumps(payload),
#         contentType="application/json",
#         accept="application/json"
#     )
    
#     # Parse the response body
#     response_body = json.loads(response['body'].read())

#     # print(response_body)
    
#     # For Claude models, the response format is different from streaming
#     if 'content' in response_body:
#         # Extract the text from the content array
#         for content_block in response_body['content']:
#             if content_block.get('type') == 'thinking':
#                 print(content_block.get('thinking', ''))
#             if content_block.get('type') == 'text':
#                 print(content_block.get('text', ''))
#     else:
#         # Fallback in case the response format is different
#         print(json.dumps(response_body, indent=2))

# except ClientError as e:
#     print("Bedrock error:", e.response["Error"]["Message"])


# import boto3, os
# import logging

# from botocore.exceptions import ClientError


# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def invoke_agent(client, agent_id, alias_id, prompt, session_id):
#         response = client.invoke_agent(
#             agentId=agent_id,
#             agentAliasId=alias_id,
#             enableTrace=True,
#             sessionId = session_id,
#             inputText=prompt,
#             streamingConfigurations = { 
#     "applyGuardrailInterval" : 20,
#       "streamFinalResponse" : False
#             }
#         )
#         completion = ""
#         for event in response.get("completion"):
#             #Collect agent output.
#             if 'chunk' in event:
#                 chunk = event["chunk"]
#                 completion += chunk["bytes"].decode()
            
#             # Log trace output.
#             if 'trace' in event:
#                 trace_event = event.get("trace")
#                 trace = trace_event['trace']
#                 for key, value in trace.items():
#                     logging.info("%s: %s",key,value)

#         print(f"Agent response: {completion}")


# if __name__ == "__main__":

#     client=boto3.client(
#             service_name="bedrock-agent-runtime",
#             region_name="us-east-2",
#             aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
#             aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")) 
    
#     agent_id = "Y81X2EDTMI"
#     alias_id = "9MU9UHNTN6"
#     session_id = "123456"
#     prompt = "Increase the temperature by 10 degrees"

#     try:

#         invoke_agent(client, agent_id, alias_id, prompt, session_id)

#     except ClientError as e:
#         print(f"Client error: {str(e)}")
#         logger.error("Client error: %s", {str(e)})



"""
Runs an Amazon Bedrock flow and handles muli-turn interaction for a single conversation.

"""
import logging
import boto3, os
import botocore


import botocore.exceptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def invoke_flow(client, flow_id, flow_alias_id, input_data, execution_id):
    """
    Invoke an Amazon Bedrock flow and handle the response stream.

    Args:
        client: Boto3 client for Amazon Bedrock agent runtime
        flow_id: The ID of the flow to invoke
        flow_alias_id: The alias ID of the flow
        input_data: Input data for the flow
        execution_id: Execution ID for continuing a flow. Use the value None on first run.

    Returns:
        Dict containing flow_complete status, input_required info, and execution_id
    """

    response = None
    request_params = None

    if execution_id is None:
        # Don't pass execution ID for first run.
        request_params = {
            "flowIdentifier": flow_id,
            "flowAliasIdentifier": flow_alias_id,
            "inputs": [input_data],
            "enableTrace": True
        }
    else:
        request_params = {
            "flowIdentifier": flow_id,
            "flowAliasIdentifier": flow_alias_id,
            "executionId": execution_id,
            "inputs": [input_data],
            "enableTrace": True
        }

    response = client.invoke_flow(**request_params)
    if "executionId" not in request_params:
        execution_id = response['executionId']

    input_required = None
    flow_status = ""

    # Process the streaming response
    for event in response['responseStream']:
        # Check if flow is complete.
        if 'flowCompletionEvent' in event:
            flow_status = event['flowCompletionEvent']['completionReason']

        # Check if more input us needed from user.
        elif 'flowMultiTurnInputRequestEvent' in event:
            input_required = event

        # Print the model output.
        elif 'flowOutputEvent' in event:
            print(event['flowOutputEvent']['content']['document'])

        elif 'flowTraceEvent' in event:
            logger.info("Flow trace:  %s", event['flowTraceEvent'])

    return {
        "flow_status": flow_status,
        "input_required": input_required,
        "execution_id": execution_id
    }


if __name__ == "__main__":

    # session = boto3.Session(profile_name='default', region_name='YOUR_FLOW_REGION')

    bedrock_agent_client=boto3.client(
        service_name="bedrock-agent-runtime",
        region_name="us-east-2",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")) 
    
    # bedrock_agent_client = session.client('bedrock-agent-runtime')
    
    # Replace these with your actual flow ID and alias ID
    FLOW_ID = 'E7JGHVUXLL'
    FLOW_ALIAS_ID = 'IVWH7TQZW0'


    flow_execution_id = None
    finished = False

    # Get the intial prompt from the user.
    user_input = input("Enter input: ")

    flow_input_data = {
        "content": {
            "document": user_input
        },
        "nodeName": "FlowInputNode",
        "nodeOutputName": "document"
    }

    logger.info("Starting flow %s", FLOW_ID)

    try:
        while not finished:
            # Invoke the flow until successfully finished.

            result = invoke_flow(
                bedrock_agent_client, FLOW_ID, FLOW_ALIAS_ID, flow_input_data, flow_execution_id)
            status = result['flow_status']
            flow_execution_id = result['execution_id']
            more_input = result['input_required']
            if status == "INPUT_REQUIRED":
                # The flow needs more information from the user.
                logger.info("The flow %s requires more input", FLOW_ID)
                user_input = input(
                    more_input['flowMultiTurnInputRequestEvent']['content']['document'] + ": ")
                flow_input_data = {
                    "content": {
                        "document": user_input
                    },
                    "nodeName": more_input['flowMultiTurnInputRequestEvent']['nodeName'],
                    "nodeInputName": "agentInputText"

                }
            elif status == "SUCCESS":
                # The flow completed successfully.
                finished = True
                logger.info("The flow %s successfully completed.", FLOW_ID)

    except botocore.exceptions.ClientError as e:
        print(f"Client error: {str(e)}")
        logger.error("Client error: %s", {str(e)})

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        logger.error("An error occurred: %s", {str(e)})
        logger.error("Error type: %s", {type(e)})
