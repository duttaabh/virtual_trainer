import os
import json
import logging

import streamlit as st
import utils.utils as utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

if 'AWS_REGION' not in os.environ:
    region = 'us-east-1'
else:
    region = os.environ['AWS_REGION']

if 'S3_BUCKET_NAME' not in os.environ:
    bucket_name = 'ab3-ad-data-processing'
else:
    bucket_name = os.environ['S3_BUCKET_NAME']

if 'DYNAMO_MEMBER_TABLE' not in os.environ:
    membertable = 'user_profiles'
else:
    membertable = os.environ['DYNAMO_MEMBER_TABLE']

if 'DYNAMO_EXERCISE_TABLE' not in os.environ:
    exercisetable = 'exercise_details'
else:
    exercisetable = os.environ['DYNAMO_EXERCISE_TABLE']

from random import randrange

if 'user_id' not in st.session_state:
    user_id = str(randrange(5))
    if int(user_id) < 1:
        user_id = str(randrange(5))
    st.session_state['user_id'] = user_id
else:
    user_id = st.session_state['user_id']
# print(user_id)

def ui_loader():
   st.set_page_config(
      page_title="Vitual Fitness Trainer",
      page_icon="images/otf.jpeg",
   )

   custom_css = """
           <style>
                   @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap');
                   html, body, p, li, a, h1, h2, h3, h4, h5, h6, table, td, th, div, form, input, button, textarea, [class*="css"] {
                       font-family: 'Inter', sans-serif;
                   }
                   .block-container {
                       padding-top: 32px;
                       padding-bottom: 32px;
                       padding-left: 0;
                       padding-right: 0;
                   }
                   textarea[class^="st-"] {
                       height: 375px;
                       font-family: 'Inter', sans-serif;
                       background-color: #777777;
                       color: #ffffff;
                   }
                   section[aria-label="Upload JPG, PNG, GIF, WEBP, PDF, CSV, or TXT files:"] {
                       background-color: #777777;
                   }
                   textarea[aria-label="Analysis:"] { # llm response
                       height: 800px;
                   }
                   .element-container img { # uploaded image preview
                       background-color: #ffffff;
                   }
                   h2 { # main headline
                       color: white;
                   }
                   MainMenu {
                       visibility: hidden;
                   }
                   footer {
                       visibility: hidden;
                   }
                   header {
                       visibility: hidden;
                   }
                   p, div, h1, h2, h3, h4, h5, h6, button, section, label, input, small[class^="st-"] {
                       color: #ffffff;
                   }
                   button, section, label, input {
                       background-color: #555555;
                   }
                   button[class^="st-"] {
                       background-color: #777777;
                       color: #ffffff;
                       border-color: #ffffff;
                   }
                   hr span {
                       color: #ffffff;
                   }
                   div[class^="st-"] {
                       color: #ccc8aa;
                   }
                   div[class^="stSlider"] p {
                       color: #ccc8aa;
                   }
                   div[class^="stSlider"] label {
                       background-color: #777777;
                   }
                   section[data-testid="stSidebar"] {
                     width: 100px !important; # Set the width to your desired value
                   }
                   div[data-testid="stSidebarUserContent"] {
                       padding-top: 40px;
                   }
                   div[class="row-widget stSelectbox"] label {
                       background-color: #777777;
                   }
                   label[data-testid="stWidgetLabel"] p {
                       color: #ccc8aa;
                   }
                   div[data-baseweb="select"] div {
                       font-size: 14px;
                   }
                   div[data-baseweb="select"] li {
                       font-size: 12px;
                   }
                   [data-testid="stForm"] {
                       border-color: #777777;
                   }
                   [id="generative-ai-powered-multimodal-analysis"] span {
                       color: #e6e6e6;
                       font-size: 34px;
                   }
                   [data-testid="stForm"] {
                       width: 850px;
                   }
           </style>
           """

   st.markdown(
      custom_css,
      unsafe_allow_html=True,
   )
   member_profile = utils.query_membership_data(region, membertable, user_id)[0]
   exercise_tracker = json.dumps(utils.query_exercise_data(region, exercisetable, user_id))
   st.header(f'Welcome {member_profile["first_name"]}, to the Virtual Fitness Center!!!')
   try:
         with st.sidebar:
            st.sidebar.markdown('<font color="black"><u><b>Available Training Videos</b></u></font>',
                                unsafe_allow_html=True)
            for file in os.listdir("videos"):
               if file.endswith(".mp4"):
                  st.sidebar.markdown(f'<font color="black" size="2"><u>{file}</u></font>', unsafe_allow_html=True)
                  st.video(os.path.join("videos", file))

         st.subheader("Member Profile")
         if 'member_profile' not in st.session_state:
            with st.spinner('Wait!! Retrieving your profile...'):
               schedule = utils.build_request(
                  f'generate a brief member profile with bullet points based on  {member_profile["first_name"]}, {member_profile["last_name"]}, {member_profile["target_weight"]} kg, actual weight {member_profile["actual_weight"]} kg, BMI {member_profile["bmi"]}, Gender {member_profile["gender"]} and Age {member_profile["age"]}, do not make up any data.',
                  [])['content'][0]['text']
               st.session_state['member_profile'] = schedule
               st.markdown(schedule, unsafe_allow_html=True)
         else:
            schedule = st.session_state['member_profile']
            st.markdown(schedule, unsafe_allow_html=True)

         st.subheader("View your personalized training schedule")
         if 'training_schedule' not in st.session_state:
            with st.spinner('Wait!! Generating your personalized schedule...'):
               schedule = utils.build_request(
                  f'Recommend a weekly fitness training schedule in html table format based on target weight {member_profile["target_weight"]} kg, actual weight {member_profile["actual_weight"]} kg, BMI {member_profile["bmi"]}, Gender {member_profile["gender"]} and Age {member_profile["age"]}, do not make up any data.',
                  [])['content'][0]['text']
               st.session_state['training_schedule'] = schedule
               # schedule_json = validateJsonResponse(schedule)
               st.markdown(schedule, unsafe_allow_html=True)
         else:
            schedule = st.session_state['training_schedule']
            st.markdown(schedule, unsafe_allow_html=True)

         st.subheader("Dive deep into your fitness details")
         if 'training_details' not in st.session_state:
            with st.spinner('Wait!! Loading your Exercise data...'):
               schedule = utils.build_request(
                  f'generate exercise insights summary in HTML format with bullet points without a header considering exercise data {exercise_tracker}, do not make up any data',
                  [])['content'][0]['text']
               # schedule_json = validateJsonResponse(schedule)
               st.session_state['training_details'] = schedule
               st.markdown(schedule, unsafe_allow_html=True)
         else:
            schedule = st.session_state['training_details']
            st.markdown(schedule, unsafe_allow_html=True)

         uploaded_files = st.file_uploader(
            "Upload exercise video(s) in mp4 format for persoalized evaluation:",
            type=["mp4"],
            accept_multiple_files=True,
         )
         if uploaded_files is not None:
            if len(uploaded_files) > 0:
               for uploaded_file in uploaded_files:
                  print(
                     uploaded_file.file_id,
                     uploaded_file.name,
                     uploaded_file.type,
                     uploaded_file.size,
                  )
                  file_path = f'videos/{uploaded_file.name}'
                  with open(file_path, 'wb') as f:
                     f.write(uploaded_file.read())
                  utils.upload_file_s3(file_path, bucket_name, f'user_{user_id}')
               st.success('Files(s) have been successfully uploaded!')

         files = ['Please select']
         for file in os.listdir("videos"):
            if file.endswith(".mp4"):
               files.append(file)
         option = st.selectbox('Choose an exercise videos from the dropdown to evaluate', options=files)
         if option and option != 'Please select':
            name = os.path.join("videos", option)
            with st.spinner('Wait!! Evaluating training Video...'):
               image_frame_paths = utils.generate_image_frames(name)
               results = utils.generate_exercise_insights(image_frame_paths)
               if results is not None:
                  col1, col2, col3 = st.columns(3)
                  col1.markdown(f"<u><b>Video Name: {option}</b></u>", unsafe_allow_html=True)
                  col1.video(name)
                  col2.markdown("<u><b>Posture Details</b></u>", unsafe_allow_html=True)
                  posture = results['insights'].replace('\n', '<br/>')
                  col2.markdown(f"<font size='2'>{posture}</font>", unsafe_allow_html=True)
                  col3.markdown("<u><b>Trainer Feedback</b></u>", unsafe_allow_html=True)
                  correction = results['correction'].replace('\n', '<br/>')
                  audio_file = utils.generate_audio_output(results['correction'], option.split('.')[0])
                  # print(audio_file)
                  col3.audio(audio_file)
                  col3.markdown(f"<font size='2'>{correction}</font>", unsafe_allow_html=True)
               else:
                  st.error("Sorry, Please try again later.")
   except Exception as e:
      import traceback
      traceback.print_exc()
      st.error("Sorry, Please try again later.")

if __name__ == "__main__":
   ui_loader()