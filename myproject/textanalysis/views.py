from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import boto3
import json
import re
import pandas as pd
from django.http import JsonResponse
from dotenv import load_dotenv, dotenv_values

load_dotenv()

# AWS credentials
aws_access_key_id = os.getenv("AWS_ACCESS")
aws_secret_access_key = os.getenv("AWS_SECRET_KEY")

# Initialize Textract and Comprehend clients
textract_client = boto3.client(
    'textract',
    region_name='us-east-1',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

comprehend_client = boto3.client(
    'comprehend',
    region_name='us-east-1',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

def home(request):
    return render(request, 'home.html')

def upload_image(request):
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        if image_file:
            try:
                # Save image file
                file_path = default_storage.save(image_file.name, ContentFile(image_file.read()))
                full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)

                # Process the image with AWS Textract
                with open(full_file_path, 'rb') as document:
                    image_bytes = document.read()

                textract_response = textract_client.detect_document_text(Document={'Bytes': image_bytes})

                extracted_text = ''
                for item in textract_response.get('Blocks', []):
                    if item.get('BlockType') == 'LINE':
                        extracted_text += item.get('Text', '') + '\n'

                # Detect entities using Comprehend
                comprehend_response = comprehend_client.detect_entities(Text=extracted_text, LanguageCode='en')
                df = pd.DataFrame(comprehend_response['Entities'])

                phone_pattern = re.compile(r'\+?\d[\d -]{8,}\d')
                email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
                website_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
                postal_code_pattern = re.compile(r'\b\d{6}\b')

                def identify_entity(row):
                    text = row['Text']
                    if row['Type'] in ['PERSON', 'ORGANIZATION', 'LOCATION']:
                        return row['Type']
                    elif phone_pattern.search(text):
                        return 'PHONE_NUMBER'
                    elif email_pattern.search(text):
                        return 'EMAIL'
                    elif website_pattern.search(text):
                        return 'WEBSITE'
                    elif postal_code_pattern.search(text):
                        return 'POSTAL_CODE'
                    else:
                        return 'OTHER'

                df['Type'] = df.apply(identify_entity, axis=1)
                df = df[['Score', 'Type', 'Text', 'BeginOffset', 'EndOffset']]

                # Store data in session
                request.session['extracted_text'] = extracted_text
                request.session['entities'] = json.dumps(df.to_dict(orient='records'))

                return JsonResponse({
                    'extracted_text': extracted_text,
                    'show_entities_button': True
                })
            except Exception as e:
                print(f"Error processing image: {e}")
                return JsonResponse({'error': 'There was an error processing the image.'})
        else:
            return JsonResponse({'error': 'No image file provided.'})
    return JsonResponse({'error': 'Invalid request method.'})

def entities(request):
    extracted_text = request.session.get('extracted_text', '')
    entities_json = request.session.get('entities', '[]')
    entities = json.loads(entities_json)
    return render(request, 'detected_entities.html', {
        'extracted_text': extracted_text,
        'entities': entities
    })
