import json
from tweet import main

def lambda_handler(event, context):
    success, tw = main()
    return {
        'statusCode': 200,
        'body': tw,
        'success': success
    }

