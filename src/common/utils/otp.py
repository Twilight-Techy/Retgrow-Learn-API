import secrets
import datetime

def generate_otp(length: int) -> str:
    """
    Generates a cryptographically secure OTP of a given length.
    
    Args:
        length (int): The length of the OTP.
    
    Returns:
        str: A zero-padded OTP as a string.
    """
    otp = secrets.randbelow(10**length)
    return str(otp).zfill(length)

def get_otp_expiry(hours: int) -> datetime.datetime:
    """
    Returns the expiry datetime for an OTP after a specified number of hours.
    
    Args:
        hours (int): The number of hours until the OTP expires.
    
    Returns:
        datetime.datetime: The expiry datetime.
    """
    return datetime.datetime.now() + datetime.timedelta(hours=hours)