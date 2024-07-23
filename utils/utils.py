from io import StringIO
import cv2
import os
import math
import boto3
import json
import logging
import base64
import pandas as pd
import matplotlib.pyplot as plt
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from boto3 import Session
from contextlib import closing

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# write a function to query data from the table
def query_membership_data(region, tablename, key_value):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(tablename)
    response = table.scan(
        FilterExpression=Attr("id").eq(key_value)
    )
    return response['Items']

# write a function to query data from the table
def query_exercise_data(region, tablename, key_value):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(tablename)
    response = table.scan(
        FilterExpression=Attr("user_id").eq(key_value)
    )
    return response['Items']

def run_multi_modal_prompt(
        bedrock_runtime,
        model_id,
        messages,
        max_tokens,
        temperature,
        top_p,
        top_k,
):
   """
   Invokes a model with a multimodal prompt.
   Args:
       bedrock_runtime: The Amazon Bedrock boto3 client.
       model_id (str): The model ID to use.
       messages (JSON) : The messages to send to the model.
       max_tokens (int) : The maximum  number of tokens to generate.
       temperature (float): The amount of randomness injected into the response.
       top_p (float): Use nucleus sampling.
       top_k (int): Only sample from the top K options for each subsequent token.
   Returns:
       response_body (string): Response from foundation model.
   """

   body = json.dumps(
      {
         "anthropic_version": "bedrock-2023-05-31",
         "max_tokens": max_tokens,
         "messages": messages,
         "temperature": temperature,
         "top_p": top_p,
         "top_k": top_k,
      }
   )

   response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
   response_body = json.loads(response.get("body").read())

   return response_body

def build_request(prompt, file_paths):
   """
   Entrypoint for Anthropic Claude multimodal prompt example.
   Args:
       prompt (str): The prompt to use.
       image (str): The image to use.
   Returns:
       response_body (string): Response from foundation model.
   """

   try:
      # print(prompt)

      bedrock_runtime = boto3.client(service_name="bedrock-runtime")

      message = {
         "role": "user",
         "content": [
            {"type": "text", "text": prompt},
         ],
      }

      if file_paths is not None:  # must be image(s)
         for file_path in file_paths:  # append each to message
            with open(file_path["file_path"], "rb") as image_file:
               content_image = base64.b64encode(image_file.read()).decode("utf8")
               message["content"].append(
                  {
                     "type": "image",
                     "source": {
                        "type": "base64",
                        "media_type": file_path["file_type"],
                        "data": content_image,
                     },
                  }
               )

         messages = [message]

      response = run_multi_modal_prompt(
         bedrock_runtime,
         'anthropic.claude-3-sonnet-20240229-v1:0',
         messages,
         1000,
         1.0,
         0.999,
         250,
      )

      # print(json.dumps(response, indent=4))
      return response
   except ClientError as err:
      message = err.response["Error"]["Message"]
      logger.error("A client error occurred: %s", message)
      print("A client error occurred: " + format(message))
      return None

def build_image_request(prompt):
   """
   Entrypoint for Anthropic Claude multimodal prompt example.
   Args:
       prompt (str): The prompt to use.
       image (str): The image to use.
   Returns:
       response_body (string): Response from foundation model.
   """

   try:
      bedrock_runtime = boto3.client(service_name="bedrock-runtime")
      message = {"text_prompts":[{"text":f"{prompt}","weight":1}],"cfg_scale":10,"steps":50,"seed":0,"width":1024,"height":1024,"samples":1}
      accept = "application/json"
      contentType = "application/json"
      response = bedrock_runtime.invoke_model(
          body=json.dumps(message), modelId='stability.stable-diffusion-xl-v1', accept=accept, contentType=contentType
      )
      response_body = json.loads(response.get("body").read())
      image_bytes = response_body.get("artifacts")[0].get("base64")
      image_data = base64.b64decode(image_bytes.encode())
      return image_data
   except ClientError as err:
      message = err.response["Error"]["Message"]
      logger.error("A client error occurred: %s", message)
      print("A client error occurred: " + format(message))
      return None

def generate_image_frames(video_filepath):
   file_paths = []
   video_filename = video_filepath[video_filepath.rindex("/") + 1: video_filepath.rindex(".")]
   image_output_folder = 'output/' + video_filename
   cam = cv2.VideoCapture(video_filepath)
   frame_rate = cam.get(cv2.CAP_PROP_FPS)

   frames_per_second = 1
   if frames_per_second > frame_rate or frames_per_second == -1:
      frames_per_second = frame_rate

   if not os.path.exists(image_output_folder):
       os.mkdir(image_output_folder)

   frameno = 0
   image_frameno = 0
   while(True):
      ret,frame = cam.read()
      if ret:
         # if video is still left continue creating images
         frate = math.floor(frame_rate / frames_per_second)
         if frameno % frate == 0:
            name = image_output_folder + '/' + video_filename + '_frame_' + str(image_frameno) + '.jpeg'
            file_paths.append({'file_path':name, 'file_type':'image/jpeg'})
            cv2.imwrite(name, frame)
            image_frameno += 1
         frameno += 1
         if frameno > 15:
            break
      else:
         break

   cam.release()
   cv2.destroyAllWindows()
   return file_paths

def generate_exercise_insights(image_frame_paths):
   exercise_details = build_request(
      'identify the exercise, provide the body angle measurements, evaluate the posture and provide feedback summary with in 20 words in bullet points',
      image_frame_paths)['content'][0]['text']
   posture_correction = build_request('please evaluate the posture and provide any correction summary in 50 words referring the customer in second person in bullet points',
                 image_frame_paths)['content'][0]['text']
   return {'insights': exercise_details, 'correction': posture_correction}

def generate_audio_output(text, filename):
   session = Session()
   polly = session.client("polly")
   response = polly.synthesize_speech(Text=text, OutputFormat="mp3",
                                      VoiceId="Joanna")
   if "AudioStream" in response:
      with closing(response["AudioStream"]) as stream:
         output = os.path.join('audio', f"{filename}.mp3")
         with open(output, "wb") as file:
            file.write(stream.read())
   return output


def validateJsonResponse(response):
   # print('response: ', response)
   if len(response) > 0:
      # try:
      if response.index('[') > -1 and response.index(']') > -1:
         start_index = response.find('[')
         end_index = response.rindex(']') + 1
         # Extract the JSON message as a string
         json_message = response[start_index:end_index]
         # print("message: ", json_message)
         # Parse the JSON message
         data = json.loads(json_message)
         # print("data: ", data)
         # data = formatJsonMessage(data)
      else:
         data = ''
   return data

def bar_chart(df, x, y):
   plt.bar(df[x], df[y])
   plt.xlabel(x)
   plt.ylabel(y)
   plt.show()


def pie_chart(df, label, value):
   plt.pie(df[value], labels=df[label])
   plt.show()


def merge_bar_charts(df, x, y1, y2):
   plt.rcParams["figure.figsize"] = [7.50, 3.50]
   plt.rcParams["figure.autolayout"] = True
   fig, ax = plt.subplots()
   df[x, y1].plot(kind='bar', color='red')
   df[x, y2].plot(kind='line', marker='*', color='black', ms=10)
   plt.show()


def upload_file_s3(file_name, bucket, prefix):
   s3_client = boto3.client('s3')
   object_name = f"{prefix}/{file_name}"
   s3_client.upload_file(file_name, bucket, object_name)

if __name__ == '__main__':
    exercise_data = query_exercise_data('us-east-1', '1')
    df = pd.read_json(StringIO(json.dumps(exercise_data)))
    merge_bar_charts(df, 'date', 'calories_burned', 'heart_rate_avg')
    # df_sql = sqldf("select replace(workout_type, 'nan', 'Rest') as workout_type, count(1) as times from df group by workout_type")
    # pie_chart(df_sql, 'workout_type', 'times')