import json
from tweet import tweet

def lambda_handler(event, context):
    tw = tweet(dynamodb=True)
    return {
        'statusCode': 200,
        'body': json.dumps(tw)
    }

