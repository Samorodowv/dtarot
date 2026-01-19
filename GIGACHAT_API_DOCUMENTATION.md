# GigaChat API Documentation

This documentation provides complete instructions and examples for using the GigaChat API (Russian AI model by Sber) in external projects.

## Table of Contents
- [API Credentials](#api-credentials)
- [Installation](#installation)
- [Authentication Methods](#authentication-methods)
- [Basic Usage Examples](#basic-usage-examples)
- [Advanced Features](#advanced-features)
- [Error Handling](#error-handling)
- [Model Selection](#model-selection)
- [Testing Your Credentials](#testing-your-credentials)

## API Credentials

### Working Credentials (from this project's .env file)
```
Client ID: 9314969a-854b-43ec-941b-85f1619d5196
Client Secret: b6699e64-9988-4161-89a9-4d03f83bcca4
Base64 Auth Key: OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA==
```

### OAuth Endpoint
```
Token URL: https://ngw.devices.sberbank.ru:9443/api/v2/oauth
API Base URL: https://gigachat.devices.sberbank.ru/api/v1
Scope: GIGACHAT_API_PERS
```

## Installation

```bash
pip install gigachat
```

Or add to your requirements.txt:
```
gigachat==0.1.29
```

## Authentication Methods

### Method 1: Using Base64 Encoded Credentials (Simplest)

```python
from gigachat import GigaChat

# Direct authentication with base64 encoded credentials
client = GigaChat(
    credentials="OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA==",
    verify_ssl_certs=False,
)
```

### Method 2: OAuth Token Management (Production-Ready)

```python
import requests
import base64
import time
from datetime import datetime, timedelta

class GigaChatAuth:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.scope = "GIGACHAT_API_PERS"
        self.access_token = None
        self.token_expires_at = None

    def get_token(self):
        """Get OAuth token with automatic refresh"""
        # Check if token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token

        # Request new token
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': f'{int(time.time())}',
            'Authorization': f'Basic {encoded}'
        }

        data = {'scope': self.scope}

        response = requests.post(
            self.token_url,
            headers=headers,
            data=data,
            verify=False
        )

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 1800)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            return self.access_token
        else:
            raise Exception(f"Failed to get token: {response.status_code} - {response.text}")

# Usage
auth = GigaChatAuth(
    client_id="9314969a-854b-43ec-941b-85f1619d5196",
    client_secret="b6699e64-9988-4161-89a9-4d03f83bcca4"
)

from gigachat import GigaChat

client = GigaChat(
    credentials=auth.get_token(),
    verify_ssl_certs=False,
)
```

## Basic Usage Examples

### Simple Chat Completion

```python
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# Initialize client
client = GigaChat(
    credentials="OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA==",
    verify_ssl_certs=False,
)

# Create chat payload
payload = Chat(
    messages=[
        Messages(
            role=MessagesRole.SYSTEM,
            content="You are a helpful assistant that speaks Russian and English."
        ),
        Messages(
            role=MessagesRole.USER,
            content="Hello! How are you?"
        )
    ],
    temperature=0.7,
    max_tokens=200,
    model="GigaChat"  # or "GigaChat-Max", "GigaChat-Pro"
)

# Get response
response = client.chat(payload)
print(response.choices[0].message.content)
```

### Conversation with Context

```python
class GigaChatConversation:
    def __init__(self, system_prompt="You are a helpful assistant."):
        self.client = GigaChat(
            credentials="OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA==",
            verify_ssl_certs=False,
        )
        self.messages = [
            Messages(role=MessagesRole.SYSTEM, content=system_prompt)
        ]

    def send_message(self, user_input: str) -> str:
        # Add user message
        self.messages.append(
            Messages(role=MessagesRole.USER, content=user_input)
        )

        # Create payload
        payload = Chat(
            messages=self.messages,
            temperature=0.7,
            max_tokens=200,
            model="GigaChat"
        )

        # Get response
        response = self.client.chat(payload)
        bot_response = response.choices[0].message

        # Add bot response to history
        self.messages.append(bot_response)

        return bot_response.content

# Usage
chat = GigaChatConversation("You are a Python programming expert.")
print(chat.send_message("How do I read a JSON file?"))
print(chat.send_message("Can you show me an example?"))
```

## Advanced Features

### Image Generation

```python
import re
import requests
import os

class GigaChatWithImages:
    def __init__(self):
        self.client = GigaChat(
            credentials="OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA==",
            verify_ssl_certs=False,
        )

    def generate_image(self, prompt: str):
        """Generate image using GigaChat"""
        # Request should include image generation keywords
        image_prompt = f"нарисуй {prompt}" if not prompt.startswith("нарисуй") else prompt

        payload = Chat(
            messages=[
                Messages(role=MessagesRole.USER, content=image_prompt)
            ],
            temperature=0.7,
            max_tokens=200,
            model="GigaChat",
            function_call="auto"
        )

        response = self.client.chat(payload)
        content = response.choices[0].message.content

        # Extract image ID from response
        image_id_match = re.search(r'<img src="([^"]+)"', content)
        if image_id_match:
            image_id = image_id_match.group(1)
            return self.download_image(image_id)

        return None

    def download_image(self, image_id: str) -> str:
        """Download generated image"""
        url = f"https://gigachat.devices.sberbank.ru/api/v1/files/{image_id}/content"
        headers = {
            'Accept': 'application/jpg',
            'Authorization': f'Bearer {self.client.token}'
        }

        response = requests.get(url, headers=headers, stream=True, verify=False)

        if response.status_code == 200:
            # Save image
            os.makedirs('generated_images', exist_ok=True)
            image_path = f'generated_images/{image_id}.jpg'

            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return image_path

        return None

# Usage
image_gen = GigaChatWithImages()
image_path = image_gen.generate_image("космический корабль в стиле киберпанк")
if image_path:
    print(f"Image saved to: {image_path}")
```

### Model Selection and Token Optimization

```python
class SmartGigaChat:
    """Automatically selects the best model based on query complexity"""

    def __init__(self):
        self.client = GigaChat(
            credentials="OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA==",
            verify_ssl_certs=False,
        )
        self.models = {
            "simple": "GigaChat",      # Basic model for simple tasks
            "complex": "GigaChat-Max",  # Advanced model for complex tasks
            "pro": "GigaChat-Pro"       # Professional model for specialized tasks
        }

    def select_model(self, query: str) -> str:
        """Select appropriate model based on query"""
        # Simple heuristic - can be improved
        query_lower = query.lower()

        # Check for complex tasks
        complex_keywords = ["анализ", "объясни", "напиши код", "создай", "разработай"]
        if any(keyword in query_lower for keyword in complex_keywords):
            return self.models["complex"]

        # Check for image generation
        if "нарисуй" in query_lower or "изображение" in query_lower:
            return self.models["complex"]

        # Default to simple model
        return self.models["simple"]

    def chat(self, query: str) -> str:
        model = self.select_model(query)
        print(f"Using model: {model}")

        payload = Chat(
            messages=[
                Messages(role=MessagesRole.USER, content=query)
            ],
            temperature=0.7,
            max_tokens=200,
            model=model
        )

        response = self.client.chat(payload)
        return response.choices[0].message.content

# Usage
smart_chat = SmartGigaChat()
print(smart_chat.chat("Привет!"))  # Uses basic model
print(smart_chat.chat("Объясни квантовую физику"))  # Uses advanced model
```

## Error Handling

```python
from gigachat.exceptions import ResponseError

def safe_gigachat_call(client, payload):
    """Safely call GigaChat API with error handling"""
    try:
        response = client.chat(payload)
        return {
            "success": True,
            "content": response.choices[0].message.content
        }

    except ResponseError as e:
        # Extract status code from error
        status_code = e.args[1] if len(e.args) > 1 else None

        if status_code == 402:
            return {
                "success": False,
                "error": "Payment required - please check your GigaChat balance"
            }
        elif status_code == 401:
            return {
                "success": False,
                "error": "Invalid credentials - please check your API keys"
            }
        else:
            return {
                "success": False,
                "error": f"API error: {status_code}"
            }

    except ValueError as e:
        if "credentials not configured" in str(e).lower():
            return {
                "success": False,
                "error": "Credentials not configured properly"
            }
        return {
            "success": False,
            "error": f"Configuration error: {str(e)}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
```

## Model Selection

### Available Models

1. **GigaChat** - Basic model
   - Best for: Simple conversations, basic questions
   - Token limit: Lower
   - Cost: Lowest

2. **GigaChat-Max** - Advanced model
   - Best for: Complex reasoning, code generation, detailed analysis
   - Token limit: Higher
   - Cost: Medium

3. **GigaChat-Pro** - Professional model
   - Best for: Specialized tasks, maximum quality
   - Token limit: Highest
   - Cost: Highest

### Model Comparison Example

```python
models_to_test = ["GigaChat", "GigaChat-Max", "GigaChat-Pro"]
query = "Write a Python function to calculate Fibonacci numbers"

for model in models_to_test:
    print(f"\n--- Testing {model} ---")
    payload = Chat(
        messages=[
            Messages(role=MessagesRole.USER, content=query)
        ],
        temperature=0.7,
        max_tokens=200,
        model=model
    )

    response = client.chat(payload)
    print(response.choices[0].message.content)
```

## Testing Your Credentials

```python
#!/usr/bin/env python3
"""Test your GigaChat credentials"""

import requests
import base64
import json

def test_credentials(client_id, client_secret):
    """Test if your GigaChat credentials work"""

    # Create auth header
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()

    # Request token
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f'Basic {encoded}'
    }

    data = {'scope': 'GIGACHAT_API_PERS'}

    response = requests.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers=headers,
        data=data,
        verify=False
    )

    if response.status_code == 200:
        print("✅ Credentials are valid!")
        token_data = response.json()

        # Test API call
        token = token_data.get('access_token')
        api_headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        models_response = requests.get(
            "https://gigachat.devices.sberbank.ru/api/v1/models",
            headers=api_headers,
            verify=False
        )

        if models_response.status_code == 200:
            models = models_response.json()
            print(f"Available models: {len(models.get('data', []))}")
            for model in models.get('data', [])[:3]:
                print(f"  - {model.get('id')}")

        return True
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

# Test with provided credentials
if __name__ == "__main__":
    test_credentials(
        client_id="9314969a-854b-43ec-941b-85f1619d5196",
        client_secret="b6699e64-9988-4161-89a9-4d03f83bcca4"
    )
```

## Environment Variables Setup

Create a `.env` file in your project:

```bash
# GigaChat Configuration
GIGACHAT_CLIENT_ID=9314969a-854b-43ec-941b-85f1619d5196
GIGACHAT_CLIENT_SECRET=b6699e64-9988-4161-89a9-4d03f83bcca4
GIGACHAT_AUTH_KEY=OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA==
GIGACHAT_MODEL=GigaChat-Max
```

Load in Python:
```python
import os
from dotenv import load_dotenv

load_dotenv()

client = GigaChat(
    credentials=os.getenv('GIGACHAT_AUTH_KEY'),
    verify_ssl_certs=False,
)
```

## Complete Working Example

```python
#!/usr/bin/env python3
"""
Complete GigaChat implementation example
Ready to use in any project
"""

import os
import re
import requests
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from gigachat.exceptions import ResponseError

class GigaChatClient:
    def __init__(self, auth_key=None):
        # Use provided key or default
        self.auth_key = auth_key or "OTMxNDk2OWEtODU0Yi00M2VjLTk0MWItODVmMTYxOWQ1MTk2OmI2Njk5ZTY0LTk5ODgtNDE2MS04OWE5LTRkMDNmODNiY2NhNA=="

        self.client = GigaChat(
            credentials=self.auth_key,
            verify_ssl_certs=False,
        )

        self.conversation = [
            Messages(
                role=MessagesRole.SYSTEM,
                content="You are a helpful AI assistant."
            )
        ]

    def chat(self, message: str, model="GigaChat-Max") -> dict:
        """Send message and get response"""
        try:
            # Add user message
            self.conversation.append(
                Messages(role=MessagesRole.USER, content=message)
            )

            # Create payload
            payload = Chat(
                messages=self.conversation,
                temperature=0.7,
                max_tokens=200,
                model=model,
                function_call="auto"
            )

            # Get response
            response = self.client.chat(payload)
            bot_response = response.choices[0].message

            # Add to conversation
            self.conversation.append(bot_response)

            # Check for images
            content = bot_response.content
            image_id_match = re.search(r'<img src="([^"]+)"', content)

            result = {
                "text": content,
                "image": None
            }

            if image_id_match:
                image_id = image_id_match.group(1)
                result["image"] = self._download_image(image_id)
                # Remove image tag from text
                result["text"] = re.sub(r'<img src="[^"]+" fuse="true"/>', '', content).strip()

            return result

        except ResponseError as e:
            status_code = e.args[1] if len(e.args) > 1 else None
            return {
                "text": f"Error: {status_code} - {str(e)}",
                "image": None,
                "error": True
            }
        except Exception as e:
            return {
                "text": f"Unexpected error: {str(e)}",
                "image": None,
                "error": True
            }

    def _download_image(self, image_id: str) -> str:
        """Download image from GigaChat"""
        url = f"https://gigachat.devices.sberbank.ru/api/v1/files/{image_id}/content"
        headers = {
            'Accept': 'application/jpg',
            'Authorization': f'Bearer {self.client.token}'
        }

        response = requests.get(url, headers=headers, stream=True, verify=False)

        if response.status_code == 200:
            os.makedirs('images', exist_ok=True)
            image_path = f'images/{image_id}.jpg'

            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return image_path

        return None

    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation = self.conversation[:1]  # Keep system prompt

# Example usage
if __name__ == "__main__":
    # Initialize client
    gigachat = GigaChatClient()

    # Interactive chat
    print("GigaChat Client Ready! (type 'quit' to exit, 'reset' to clear history)")

    while True:
        user_input = input("\nYou: ")

        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'reset':
            gigachat.reset_conversation()
            print("Conversation reset!")
            continue

        # Get response
        response = gigachat.chat(user_input)

        print(f"Bot: {response['text']}")

        if response.get('image'):
            print(f"Image saved: {response['image']}")
```

## Troubleshooting

### Common Issues and Solutions

1. **401 Unauthorized**
   - Check if credentials are correct
   - Verify account is activated at https://developers.sber.ru/studio

2. **402 Payment Required**
   - Check GigaChat balance
   - Top up account if needed

3. **SSL Certificate Errors**
   - Make sure `verify_ssl_certs=False` is set
   - Or provide proper SSL certificates

4. **Connection Timeouts**
   - Check internet connection
   - Verify firewall settings
   - Try using VPN if in restricted region

5. **Model Not Available**
   - Some models require special access
   - Start with "GigaChat" basic model
   - Contact support for Pro model access

## Additional Resources

- Official GigaChat Documentation: https://developers.sber.ru/docs/ru/gigachat
- API Reference: https://developers.sber.ru/docs/ru/gigachat/api/reference
- Python SDK: https://github.com/ai-forever/gigachat
- Developer Portal: https://developers.sber.ru/studio

## Support

For issues with this documentation or the example code, please refer to the main project repository.
For GigaChat API issues, contact Sber support through the developer portal.