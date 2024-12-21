# main.py
from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackContext
)
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from click import (
    generate_auth_header,
    create_card_token,
    verify_card_token,
    payment_with_token,
)
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class PaymentBot:
    def __init__(self):
        # Bot configuration
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.service_id = int(os.getenv("SERVICE_ID"))
        self.merchant_id = int(os.getenv("MERCHANT_ID"))
        self.secret_key = os.getenv("SECRET_KEY")
        self.merchant_user_id = int(os.getenv("MERCHANT_USER_ID"))
        
        # Generate auth header
        self.auth = generate_auth_header(self.merchant_user_id, self.secret_key)
        
        # Initialize bot
        self.updater = None
        self.setup_bot()

    def setup_bot(self):
        """Initialize bot with error handling"""
        try:
            self.updater = Updater(token=self.token, use_context=True)
            self.dp = self.updater.dispatcher
            self.setup_handlers()
        except Exception as e:
            logger.error(f"Bot initialization error: {str(e)}")
            raise

    def setup_handlers(self):
        """Set up all message handlers"""
        try:
            self.dp.add_handler(CommandHandler("start", self.start))
            self.dp.add_handler(MessageHandler(Filters.contact, self.handle_contact))
            self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_input))
            self.dp.add_error_handler(self.error_handler)
        except Exception as e:
            logger.error(f"Handler setup error: {str(e)}")
            raise

    def start(self, update: Update, context: CallbackContext):
        """Start command handler"""
        try:
            keyboard = [[KeyboardButton("📞 Kontakt yuborish", request_contact=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            update.message.reply_text(
                "Botimizga xush kelibsiz! Iltimos, kontakt ma'lumotlaringizni yuboring.",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Start command error: {str(e)}")
            self.send_error_message(update)

    def handle_contact(self, update: Update, context: CallbackContext):
        """Handle user contact information"""
        try:
            user_contact = update.message.contact.phone_number
            context.user_data['phone_number'] = user_contact
            keyboard = [["💳 Hisobni to'ldirish", "💵 Pul yechish"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            update.message.reply_text("Menyu:", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Contact handling error: {str(e)}")
            self.send_error_message(update)

    def handle_input(self, update: Update, context: CallbackContext):
        """Handle all text input from user"""
        try:
            text = update.message.text
            if text == "💳 Hisobni to'ldirish":
                self.start_payment_process(update, context)
            elif text == "💵 Pul yechish":
                update.message.reply_text("Pul yechish funksiyasi hozircha mavjud emas.")
            elif 'next_step' in context.user_data:
                self.process_payment_step(update, context)
        except Exception as e:
            logger.error(f"Input handling error: {str(e)}")
            self.send_error_message(update)

    def start_payment_process(self, update: Update, context: CallbackContext):
        """Start the payment process"""
        update.message.reply_text("Iltimos, Spin Bet ID ni kiriting:")
        context.user_data['next_step'] = 'get_spinbet_id'

    def process_payment_step(self, update: Update, context: CallbackContext):
        """Process each step of the payment"""
        try:
            step = context.user_data['next_step']
            if step == 'get_spinbet_id':
                context.user_data['spinbet_id'] = update.message.text
                update.message.reply_text("To'ldiriladigan summani kiriting:")
                context.user_data['next_step'] = 'get_amount'
            elif step == 'get_amount':
                if self.validate_amount(update.message.text):
                    context.user_data['amount'] = update.message.text
                    update.message.reply_text("Karta raqamini kiriting:")
                    context.user_data['next_step'] = 'get_card_number'
            elif step == 'get_card_number':
                if self.validate_card_number(update.message.text):
                    context.user_data['card_number'] = update.message.text.replace(" ", "")
                    update.message.reply_text("Karta amal qilish muddatini kiriting (MMYY format):")
                    context.user_data['next_step'] = 'get_expiry_date'
            elif step == 'get_expiry_date':
                self.handle_card_token_creation(update, context)
            elif step == 'verify_sms_code':
                self.complete_payment(update, context)
        except Exception as e:
            logger.error(f"Payment step processing error: {str(e)}")
            self.send_error_message(update)

    def validate_amount(self, amount: str) -> bool:
        """Validate payment amount"""
        try:
            float_amount = float(amount)
            if float_amount <= 0:
                raise ValueError("Amount must be positive")
            return True
        except ValueError:
            return False

    def validate_card_number(self, card_number: str) -> bool:
        """Validate card number"""
        card_number = card_number.replace(" ", "")
        return card_number.isdigit() and len(card_number) == 16

    def handle_card_token_creation(self, update: Update, context: CallbackContext):
        """Handle card token creation"""
        try:
            response = create_card_token(
                self.service_id,
                context.user_data['card_number'],
                update.message.text,
                1,
                self.auth
            )
            if response.get("error_code") == 0:
                context.user_data['card_token'] = response["card_token"]
                update.message.reply_text("SMS kodini kiriting:")
                context.user_data['next_step'] = 'verify_sms_code'
            else:
                update.message.reply_text(f"Xatolik: {response.get('error_note')}")
                context.user_data.clear()
        except Exception as e:
            logger.error(f"Card token creation error: {str(e)}")
            self.send_error_message(update)

    def complete_payment(self, update: Update, context: CallbackContext):
        """Complete the payment process"""
        try:
            verify_response = verify_card_token(
                self.service_id,
                context.user_data['card_token'],
                update.message.text,
                self.auth
            )
            if verify_response.get("error_code") == 0:
                self.process_verified_payment(update, context)
            else:
                update.message.reply_text(f"SMS tasdiqlashda xatolik: {verify_response.get('error_note')}")
        except Exception as e:
            logger.error(f"Payment completion error: {str(e)}")
            self.send_error_message(update)
        finally:
            context.user_data.clear()

    def process_verified_payment(self, update: Update, context: CallbackContext):
        """Process payment after verification"""
        try:
            payment_response = payment_with_token(
                self.service_id,
                context.user_data['card_token'],
                float(context.user_data['amount']),
                context.user_data['spinbet_id'],
                self.auth
            )
            if payment_response.get("error_code") == 0:
                update.message.reply_text("Hisobingiz muvaffaqiyatli to'ldirildi!")
            else:
                update.message.reply_text(f"To'lovda xatolik: {payment_response.get('error_note')}")
        except Exception as e:
            logger.error(f"Verified payment processing error: {str(e)}")
            self.send_error_message(update)

    def send_error_message(self, update: Update):
        """Send generic error message to user"""
        try:
            update.message.reply_text("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")

    def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        self.send_error_message(update)

    def run(self):
        """Start the bot"""
        try:
            self.updater.start_polling()
            logger.info("Bot started successfully")
            self.updater.idle()
        except Exception as e:
            logger.error(f"Bot running error: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        bot = PaymentBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")