"""
Django management command to validate GigaChat credentials and test API connectivity
Usage: python manage.py validate_gigachat
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from decouple import config
import logging

from tarot_readings.gigachat_auth import test_gigachat_credentials, GigaChatAuth
from tarot_readings.model_selector import model_selector
from tarot_readings.exceptions import GigaChatException


class Command(BaseCommand):
    help = 'Validate GigaChat API credentials and test connectivity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            type=str,
            help='GigaChat Client ID (overrides environment variable)'
        )
        parser.add_argument(
            '--client-secret',
            type=str,
            help='GigaChat Client Secret (overrides environment variable)'
        )
        parser.add_argument(
            '--test-models',
            action='store_true',
            help='Test all available models'
        )
        parser.add_argument(
            '--test-selector',
            action='store_true',
            help='Test model selector with sample queries'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        # Configure logging
        if options['verbose']:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        self.stdout.write(self.style.HTTP_INFO("🚀 GigaChat API Validation Tool"))
        self.stdout.write("=" * 50)

        try:
            # Get credentials
            client_id = options.get('client_id') or config('GIGACHAT_CLIENT_ID', default='')
            client_secret = options.get('client_secret') or config('GIGACHAT_CLIENT_SECRET', default='')

            if not client_id or not client_secret:
                raise CommandError(
                    "❌ GigaChat credentials not found. "
                    "Please set GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET environment variables "
                    "or use --client-id and --client-secret arguments."
                )

            # Display configuration
            self.stdout.write("\n📋 Current Configuration:")
            self.stdout.write(f"  Client ID: {client_id[:8]}...{client_id[-4:]}")
            self.stdout.write(f"  Client Secret: {'*' * 8}...{client_secret[-4:]}")
            self.stdout.write(f"  Default Model: {getattr(settings, 'GIGACHAT_DEFAULT_MODEL', 'GigaChat-Max')}")
            self.stdout.write(f"  Auto Model Selection: {getattr(settings, 'GIGACHAT_ENABLE_AUTO_MODEL_SELECTION', True)}")
            self.stdout.write(f"  Timeout: {getattr(settings, 'GIGACHAT_TIMEOUT', 30)}s")
            self.stdout.write(f"  Max Retries: {getattr(settings, 'GIGACHAT_MAX_RETRIES', 3)}")

            # Test basic credentials
            self.stdout.write("\n🔐 Testing Credentials...")
            if test_gigachat_credentials(client_id, client_secret):
                self.stdout.write(self.style.SUCCESS("✅ Credentials are valid!"))
            else:
                raise CommandError("❌ Credential validation failed!")

            # Test OAuth token generation
            self.stdout.write("\n🎫 Testing OAuth Token Generation...")
            auth = GigaChatAuth(client_id, client_secret)
            token = auth.get_token()
            if token:
                self.stdout.write(self.style.SUCCESS(f"✅ OAuth token generated successfully"))
                self.stdout.write(f"  Token (first 20 chars): {token[:20]}...")
                self.stdout.write(f"  Token expires at: {auth.token_expires_at}")
            else:
                raise CommandError("❌ Failed to generate OAuth token!")

            # Test model selector if requested
            if options['test_selector']:
                self.stdout.write("\n🤖 Testing Model Selector...")
                test_queries = [
                    "Привет!",
                    "Что означает карта Дурак в раскладе?",
                    "Дай мне глубокий анализ расклада на отношения",
                    "нарисуй карту таро",
                    "Объясни значение Аркан Смерть в прямом положении"
                ]

                for query in test_queries:
                    selected_model = model_selector.select_model(query)
                    explanation = model_selector.explain_selection(query, selected_model)
                    self.stdout.write(f"  Query: '{query[:30]}...'")
                    self.stdout.write(f"  Selected: {selected_model}")
                    self.stdout.write(f"  Reason: {explanation}")
                    self.stdout.write("")

            # Test models if requested
            if options['test_models']:
                self.stdout.write("\n🧪 Testing Available Models...")
                from gigachat import GigaChat
                from gigachat.models import Chat, Messages, MessagesRole

                # Use OAuth for testing
                client = GigaChat(
                    credentials=token,
                    verify_ssl_certs=False,
                )

                test_query = "Привет! Как дела?"
                models_to_test = ['GigaChat', 'GigaChat-Max']  # Test basic models

                for model_name in models_to_test:
                    try:
                        self.stdout.write(f"\n  Testing {model_name}...")

                        payload = Chat(
                            messages=[
                                Messages(role=MessagesRole.USER, content=test_query)
                            ],
                            temperature=0.7,
                            max_tokens=50,
                            model=model_name
                        )

                        response = client.chat(payload)
                        if response and response.choices:
                            content = response.choices[0].message.content
                            self.stdout.write(self.style.SUCCESS(f"    ✅ {model_name}: {content[:60]}..."))
                        else:
                            self.stdout.write(self.style.WARNING(f"    ⚠️ {model_name}: Empty response"))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"    ❌ {model_name}: {str(e)[:80]}..."))

            # Final success message
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("🎉 GigaChat validation completed successfully!"))
            self.stdout.write("\n📝 Next steps:")
            self.stdout.write("  1. Your GigaChat configuration is working correctly")
            self.stdout.write("  2. You can now use the enhanced tarot interpreter")
            self.stdout.write("  3. Check logs for detailed API interaction information")

        except GigaChatException as e:
            raise CommandError(f"❌ GigaChat API Error: {str(e)}")
        except Exception as e:
            raise CommandError(f"❌ Unexpected error: {str(e)}")

    def print_model_info(self):
        """Print information about available models"""
        self.stdout.write("\n🤖 Available Models:")
        for model_type, model_info in model_selector.models.items():
            self.stdout.write(f"  {model_info['name']} ({model_type}):")
            self.stdout.write(f"    Description: {model_info['description']}")
            self.stdout.write(f"    Best for: {', '.join(model_info['best_for'][:3])}")
            self.stdout.write(f"    Cost: {model_info['cost']}")
            self.stdout.write("")