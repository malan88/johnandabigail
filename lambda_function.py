import json
from tweet import tweet

def lambda_handler(event, context):
    success, tw = main()
    return {
        'statusCode': 200,
        'body': json.dumps(tw),
        'success': success
    }

