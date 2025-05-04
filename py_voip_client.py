from pyVoIP.VoIP import VoIPPhone, InvalidStateError, CallState
import time
import wave
import config
import socket
import requests

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
        with wave.open(f'audio/{filename}.wav', 'rb') as f:
            frames = f.getnframes()
            data = f.readframes(frames)
            call.write_audio(data)
    except Exception as e:
        print(f"Error playing {filename}: {e}")

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
        color = int(parts[2])
        
        return (x, y, color)
    except (ValueError, IndexError):
        return None

def set_pixel(x, y, color):
    """Send pixel update request to the server."""
    try:
        response = requests.get(f"{config.PIXELEBBE_URL}/pixel/{x}/{y}/{color}")
        return str(response.status_code)[0] == "2"
    except Exception as e:
        print(f"Error setting pixel: {e}")
        return False

def answer(call):
    try:
        call.answer()
        
        # Play welcome message
        play_audio(call, 'welcome')
        
        for attempt in range(config.MAX_RETRIES):
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
                if attempt < config.MAX_RETRIES - 1:  # Don't play tryagain on last attempt
                    play_audio(call, 'tryagain')
                continue
            
            # Valid input received
            x, y, color = pixel_data
            
            # Inform user we're processing
            play_audio(call, 'saving')
            
            # Try to set the pixel
            if set_pixel(x, y, color):
                play_audio(call, 'success')
            else:
                play_audio(call, 'error')
            
            break  # Exit the loop after processing valid input
        
        # Play goodbye message and hang up
        play_audio(call, 'bye')
        time.sleep(5)  # Give the audio time to play
        call.hangup()
        
    except InvalidStateError:
        pass
    except Exception as e:
        print(f"Error in call handler: {e}")
        try:
            play_audio(call, 'error')
            play_audio(call, 'bye')
            call.hangup()
        except:
            pass

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"Using local IP: {local_ip}")
    phone = VoIPPhone(config.SIP_DOMAIN, config.SIP_PORT, config.SIP_USER, config.SIP_PASSWORD, myIP=local_ip, callCallback=answer)
    phone.start()
    input('Press enter to disable the phone')
    phone.stop()