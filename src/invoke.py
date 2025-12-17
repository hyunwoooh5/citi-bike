import boto3
import json

lambda_client = boto3.client('lambda')

customer = {
  "station": "W 21 St & 6 Ave",
  "rideable_type": "classic_bike",
  "target_date": "2025-03-01"
}

response = lambda_client.invoke(
    FunctionName='citibike-docker',
    InvocationType='RequestResponse',
    Payload=json.dumps(customer)
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
