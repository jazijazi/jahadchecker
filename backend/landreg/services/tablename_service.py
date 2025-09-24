import re
from uuid import uuid4

from typing import Tuple

TableName = str

def validate_word_as_database_tablename(word:str)-> Tuple[bool, str]:
    
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', word):
        return False , "فقط حروف لاتین و اعداد و آندرلاین برای نام لایه مجاز است و نباید با عدد شروع بشود"
    
    return True , ""

def add_unique_suffix_to_layername(originallayername:str) -> TableName:
    """
        add a random unique suffix to the end of tablename for uniqueness
    """
    random_suffix = uuid4().hex[:8]

    result = f"{originallayername}_{random_suffix}" 

    return result

