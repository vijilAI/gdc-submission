import pandas as pd
import json
import os

DEMOGRAPHIC_INFO_COLS= [
       'Please select your preferred language:',
       'How old are you?',
       'What is your gender?',
       'What best describes where you live?',
       'What religious group or faith do you most identify with?',
       'What country or region do you most identify with?'
]

GENERAAL_AI_FEELING = [
       'Overall, would you say the increased use of artificial intelligence (AI) in daily life makes you feel…'
]



def process_raw_data(fname):
    participant_data = pd.read_csv(fname)

    # Get the ennglish vs raw data response.
    english_response_cols = [x for x in participant_data.columns if '(English)' in x]
    raw_langauge_response_cols = [x for x in participant_data.columns if '(Original)' in x ]

    output_json = []
    ouput_json_language = []

    for index, row in participant_data.iterrows():
        new_dict = {}
        new_dict_original_language = {}
        demographic_info = {}
        demographic_info['preferred language'] = row[DEMOGRAPHIC_INFO_COLS[0]]
        demographic_info['age bracket'] = row[DEMOGRAPHIC_INFO_COLS[1]]
        demographic_info['gender'] = row[DEMOGRAPHIC_INFO_COLS[2]]
        demographic_info['community type'] = row[DEMOGRAPHIC_INFO_COLS[3]]
        demographic_info['religion'] = row[DEMOGRAPHIC_INFO_COLS[4]]
        demographic_info['self identified country'] = row[DEMOGRAPHIC_INFO_COLS[5]]

        survey_responses_english = {}
        for col in english_response_cols:
            cleaned = col.replace("(English)", "")
            survey_responses_english[cleaned] = row[col]
        
        survey_responses_original = {}
        for col in raw_langauge_response_cols:
            cleaned = col.replace("(Original)", "")
            survey_responses_original[cleaned] = row[col]
        
        new_dict['high_level_AI_view'] = row[GENERAAL_AI_FEELING[0]]    
        new_dict['demographic_info'] = demographic_info
        new_dict['survey_responses'] = survey_responses_english
        new_dict['participant_id'] = row['Participant Id']
        new_dict['response_language'] = 'English'

        new_dict_original_language['high_level_AI_view'] = row[GENERAAL_AI_FEELING[0]]    

        new_dict_original_language['demographic_info'] = demographic_info
        new_dict_original_language['survey_responses'] = survey_responses_original

        new_dict_original_language['participant_id'] = row['Participant Id']
        new_dict_original_language['response_language'] = demographic_info['preferred language']

        output_json.append(new_dict)
        ouput_json_language.append(new_dict_original_language)
    return output_json, ouput_json_language

def generate_persona_json(dic, directory="baseline_personas"):
    filename = '%s_%s.json' % (dic['participant_id'], dic['response_language'])
    full_path = os.path.join(directory, filename)
    with open(full_path, 'w+') as fp:
        json.dump(dic, fp, indent = 4)
