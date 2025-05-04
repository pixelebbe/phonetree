from pyVoIP.VoIP import VoIPPhone, InvalidStateError, CallState
import time
import wave
import config
import socket
import requests
import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/phonetree_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def play_audio(call, filename):
    try:
        with wave.open(f'{config.AUDIO_DIR}/{filename}.wav', 'rb') as f:
            frames = f.getnframes()
            data = f.readframes(frames)
            call.write_audio(data)
    except Exception as e:
        logger.error(f"Error playing audio {filename}: {e}")

def collect_input(call, max_digits=20):
    """Collect DTMF input until * is pressed or max_digits is reached."""
    digits = []
    while len(digits) < max_digits and call.state == CallState.ANSWERED:
        dtmf = call.get_dtmf()
        if dtmf:
            digits.append(dtmf)
            if dtmf == '*':
                break
        time.sleep(0.1)
    return ''.join(digits)

def parse_pixel_input(input_str):
    """Parse input in format #x#y#color*"""
    try:
        # Find the first # and remove everything before it
        start_idx = input_str.find('#')
        if start_idx == -1:
            return None
        
        # Split the remaining string by #
        parts = input_str[start_idx+1:].split('#')
        if len(parts) != 3:
            return None
        
        # Last part should end with *
        if not parts[2].endswith('*'):
            return None
        
        # Remove the * from the color part
        parts[2] = parts[2].rstrip('*')
        
        # Convert to integers
        x = int(parts[0])
        y = int(parts[1])
        color = config.PIXELEBBE_SUPPORTED_COLORS[int(parts[2])]
        
        return (x, y, color)
    except (ValueError, IndexError):
        return None

def set_pixel(x, y, color):
    """Send pixel update request to the server."""
    try:
        requesturl = f"{config.PIXELEBBE_URL}/api/setpixel?public_key={config.PIXELEBBE_PUBLIC_KEY}&event={config.PIXELEBBE_EVENT_SLUG}&color={color}&x={x}&y={y}"
        response = requests.post(requesturl,
            data={"private_key": config.PIXELEBBE_PRIVATE_KEY})
        logger.info(f"Posted data: {requesturl}, got: {response.content}")
        return str(response.status_code)[0] == "2"
    except Exception as e:
        logger.error(f"Failed to set pixel (x={x}, y={y}, color={color}): {e}")
        return False

def answer(call):
    try:
        call.answer()
        result = {"success": False, "x": None, "y": None, "color": None}
        attempts = 0
        
        # Play welcome message
        play_audio(call, 'welcome')
        
        for attempt in range(config.MAX_RETRIES):
            attempts = attempt + 1
            # Ask for input
            play_audio(call, 'input')
            
            # Collect input
            user_input = collect_input(call)
            if not user_input:
                continue
            
            # Parse input
            pixel_data = parse_pixel_input(user_input)
            
            if pixel_data is None:
                # Invalid input
                play_audio(call, 'invalid')
                if attempt < config.MAX_RETRIES - 1:
                    play_audio(call, 'tryagain')
                continue
            
            # Valid input received
            x, y, color = pixel_data
            result.update({"x": x, "y": y, "color": color})
            
            # Inform user we're processing
            play_audio(call, 'saving')
            
            # Try to set the pixel
            if set_pixel(x, y, color):
                result["success"] = True
                play_audio(call, 'success')
            else:
                play_audio(call, 'error')
            
            break  # Exit the loop after processing valid input
        
        # Play goodbye message and hang up
        play_audio(call, 'bye')
        time.sleep(6)  # Give the audio time to play
        call.hangup()

        # Log the call outcome
        if result["success"]:
            logger.info(f"Call completed: pixel set at x={result['x']}, y={result['y']}, color={result['color']} after {attempts} attempts.")
        else:
            if result["x"] is not None:
                logger.error(f"Call failed: could not set pixel at x={result['x']}, y={result['y']}, color={result['color']} after {attempts} attempts.")
            else:
                logger.error(f"Call failed: no valid input received after {attempts} attempts.")
        
    except InvalidStateError:
        logger.error("Call failed: invalid call state")
    except Exception as e:
        logger.error(f"Call failed: unexpected error - {str(e)}")
        try:
            play_audio(call, 'error')
            play_audio(call, 'bye')
            call.hangup()
        except:
            pass

if __name__ == '__main__':
    local_ip = get_local_ip()
    logger.info(f"Starting phone tree service on {local_ip}")
    phone = VoIPPhone(config.SIP_DOMAIN, config.SIP_PORT, config.SIP_USER, config.SIP_PASSWORD, myIP=local_ip, callCallback=answer)
    phone.start()
    try:
        input('Press enter to disable the phone')
    except KeyboardInterrupt:
        pass
    finally:
        phone.stop()
        logger.info("Phone tree service stopped")