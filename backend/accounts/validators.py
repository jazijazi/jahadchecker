import re
from django.core.exceptions import ValidationError

class CustomPasswordValidator:
    """
    Custom password validator with configurable requirements.
    ! set AUTH_PASSWORD_VALIDATORS in setting file 
    """
    def __init__(self, min_length=8, require_uppercase=True, require_lowercase=True, 
                 require_numbers=True, require_special_chars=True):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_numbers = require_numbers
        self.require_special_chars = require_special_chars
    
    def validate(self, password, user=None):
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"طول رمزعبور حداقل {self.min_length} باشد")
        
        if self.require_uppercase and not any(char.isupper() for char in password):
            errors.append("رمزعبور باید شامل حروف بزرگ لاتین باشد")
        
        if self.require_lowercase and not any(char.islower() for char in password):
            errors.append("رمزعبور باید شامل حروف کوچک لاتین باشد")
        
        if self.require_numbers and not any(char.isdigit() for char in password):
            errors.append("رمزعبور باید شامل اعداد باشد")
        
        if self.require_special_chars and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("رمزعبور باید شامل کاراکترهای خاص باشد")
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        help_text = "رمز عبور باید شامل:\n"
        help_text += f"- طول رمزعبور باید حداقل {self.min_length} باشد\n"
        
        if self.require_uppercase:
            help_text += "- حداقل یک حرف بزرگ لاتین\n"
        
        if self.require_lowercase:
            help_text += "- حداقل یک حرف کوچک لاتین\n"
        
        if self.require_numbers:
            help_text += "- حداقل یک عدد\n"
        
        if self.require_special_chars:
            help_text += "- حداقل یک کاراکتر خاص (!@#$%^&*(),.?\":{}|<>)\n"
        
        return help_text