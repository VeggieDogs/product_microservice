import os
import boto3
import json
from dotenv import load_dotenv
load_dotenv()

def invoke_lambda(event_payload):
    client = boto3.client(
        'lambda', 
        region_name='us-east-1',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        )
    response = client.invoke(
        FunctionName='email',
        InvocationType='Event',
        Payload=json.dumps(event_payload)
    )
    return response

if __name__ == '__main__':
    response = invoke_lambda({'to_emails': 'ranhenryli@gmail.com'})
    print(response)