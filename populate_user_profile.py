import time

import boto3
import json
import os
import pandas as pd

if 'AWS_REGION' not in os.environ:
    region = 'us-east-1'
else:
    region = os.environ['AWS_REGION']

def create_table(table_name, region):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'
                }
            ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
                }
            ],
        BillingMode='PAY_PER_REQUEST'
    )
    time.sleep(10)
    return table

def insertDynamoItem(tablename, item_lst):
    for record in item_lst:
        tablename.put_item(Item=record)
    print('Success')

if __name__ == '__main__':
    df_members = pd.read_csv('user_profiles.csv').astype(str)
    df_trackers = pd.read_csv('exercise_details.csv').astype(str)

    df_members_json = json.loads(
        df_members.to_json(orient='records')
    )
    df_trackers_json = json.loads(
        df_trackers.to_json(orient='records')
    )

    lst_Dics = [{'item': df_members_json, 'table': 'user_profiles'},
                {'item': df_trackers_json, 'table': 'exercise_details'}]

    for element in lst_Dics:
        insertDynamoItem(create_table(table_name=element['table'], region=region), element['item'])
