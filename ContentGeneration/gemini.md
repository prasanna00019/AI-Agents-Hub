To use the free tier of the Nano Banana (Gemini 3.1 Flash Image) API for image generation, use the google-genai Python SDK. [1, 2] 
1. Install the SDK
Make sure you have the latest version of the Google Gen AI library installed: [3] 

pip install -U google-genai

2. Python Code Example
This script initializes the client and sends a text prompt to generate an image. You will need your API key from Google AI Studio. [1, 4] 

from google import genaifrom google.genai import typesimport PIL.Imagefrom io import BytesIO
# Initialize the client with your API Keyclient = genai.Client(api_key="YOUR_API_KEY_HERE")
# Define your promptprompt = "A futuristic city with banana-shaped skyscrapers, digital art style"
# Invoke the model (Gemini 3.1 Flash Image is the standard 'Nano Banana' model)response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[prompt],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="1:1"  # Options include "1:1", "4:3", "16:9", etc.
        )
    )
)
# Process and save the generated imagefor part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        # Convert raw bytes to a PIL image and save
        image = PIL.Image.open(BytesIO(part.inline_data.data))
        image.save("nano_banana_output.png")
        print("Image saved as 'nano_banana_output.png'")


Key Configuration Notes

* Model ID: Use gemini-3.1-flash-image-preview for the standard Nano Banana model.
* Response Modalities: Specify ["IMAGE"] in the configuration to receive image data.
* Free Limits: The free tier has a quota of 10 requests per minute and 500 requests per day. 

