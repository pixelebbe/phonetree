from pyVoIP.VoIP import VoIPPhone, InvalidStateError, CallState
import time
import wave
import config
import socket
import requests
import logging
import os
import random
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG_MODE else logging.INFO,
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

def play_audio(call, filename, magic=1):
    try:
        with wave.open(f'{config.AUDIO_DIR}/{filename}.wav', 'rb') as f:
            # Get audio parameters
            n_frames = f.getnframes()
            frame_rate = f.getframerate()
            # Calculate duration in seconds
            duration = n_frames / frame_rate / magic
            # Read and play the audio
            frames = n_frames // magic
            data = f.readframes(frames)
            call.write_audio(data)
            # Sleep for the duration of the audio
            time.sleep(duration)
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
    initial_input = input_str
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
        color = config.PIXELEBBE_SUPPORTED_COLORS[int(parts[2])-1]
        
        logger.debug(f"Parsed pixel input: x={x}, y={y}, color={color} from {initial_input}")
        return (x, y, color)
    except (ValueError, IndexError):
        return None

def set_pixel(x, y, color):
    """Send pixel update request to the server."""
    try:
        requesturl = f"{config.PIXELEBBE_URL}/api/setpixel?public_key={config.PIXELEBBE_PUBLIC_KEY}&event={config.PIXELEBBE_EVENT_SLUG}&color={color}&x={x}&y={y}&grid=canv"
        response = requests.post(requesturl,
            data={"private_key": config.PIXELEBBE_PRIVATE_KEY})
        logger.info(f"Posted data: {requesturl}, got: {response.content}")
        return str(response.status_code)[0] == "2"
    except Exception as e:
        logger.error(f"Failed to set pixel (x={x}, y={y}, color={color}): {e}")
        return False

def answer(call):
    origin = call.request.headers['From']
    try:
        logger.info(f"Handling incoming call from {origin['caller']} ({origin['number']}@{origin['host']}).")
        logger.debug(f"Full 'from' header: {str(origin)}")
        call.answer()
        result = {"success": False, "x": None, "y": None, "color": None}
        attempts = 0
        
        # make user wait for random amount of time
        magic = random.randint(1, 8)
        logger.info(f"Making {origin['number']}@{origin['host']} wait for 1/{magic} of the waiting message. hehe :3")
        play_audio(call, 'waiting', magic)

        time.sleep(0.5)

        # Play welcome message
        play_audio(call, 'welcome')
        
        for attempt in range(config.MAX_RETRIES):
            call.get_dtmf(length=1000) # Clear the dtmf buffer
            
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
        time.sleep(1)
        call.hangup()

        # Log the call outcome
        if result["success"]:
            logger.info(f"Call completed: {origin['number']}@{origin['host']} had {attempts} attempts and set a pixel at x={result['x']}, y={result['y']}, color={result['color']}.")
        else:
            if result["x"] is not None:
                logger.error(f"Call failed: {origin['number']}@{origin['host']} had {attempts} attempts and failed to set a pixel at x={result['x']}, y={result['y']}, color={result['color']}.")
            else:
                logger.error(f"Call failed: {origin['number']}@{origin['host']} had {attempts} attempts and provided no valid input.")
        
    except InvalidStateError:
        logger.error(f"Call failed: {origin['number']}@{origin['host']} produced an invalid call state")
    except Exception as e:
        logger.error(f"Call failed: {origin['number']}@{origin['host']} produced an unexpected error - {str(e)}")
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